from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from support import started_config

from domain.game_night.models.game_registry import GAME_STATE_TYPES
from infrastructure.database import all_models  # noqa: F401  (toutes les tables)
from infrastructure.database.database import Database
from infrastructure.database.models.game_night.game_night_model import GameNightModel
from infrastructure.repositories.game_night.game_config_mapper import (
    common_session_fields,
    game_config_from_payload,
    game_config_to_payload,
    join_payload,
    split_payload,
)
from infrastructure.repositories.game_night.game_state_tables import GAME_STATE_TABLES
from infrastructure.repositories.game_night.postgresql_game_config import (
    PostgreSQLGameConfigRepository,
)

BACK_DIR = Path(__file__).resolve().parents[1]
START_MS = 1_000


def _fair_price_in_progress():
    config = started_config("fair_price")
    config, _ = config.pull_events()
    return config.start_fair_price_turn(START_MS).pull_events()[0]


@pytest.fixture
def database() -> Iterator[Database]:
    with tempfile.TemporaryDirectory() as directory:
        db = Database(f"sqlite+aiosqlite:///{Path(directory) / 'night.db'}")
        asyncio.run(db.create_schema())
        yield db
        asyncio.run(db.dispose())


def test_every_game_has_its_own_table_and_the_night_a_column_per_common_field() -> None:
    assert set(GAME_STATE_TABLES) == set(GAME_STATE_TYPES)
    assert all(model.__tablename__ == f"{key}_games" for key, model in GAME_STATE_TABLES.items())
    columns = {column.name for column in GameNightModel.__table__.columns}
    # Un champ ajouté à `GameSession` sans colonne (ni migration) fait échouer ce test.
    assert {"session_updated_at" if name == "updated_at" else name for name in common_session_fields()} <= columns


def test_split_and_join_are_inverse() -> None:
    payload = game_config_to_payload(_fair_price_in_progress())

    assert join_payload(split_payload(payload)) == payload


def test_a_night_round_trips_through_its_tables(database: Database) -> None:
    config = _fair_price_in_progress()

    async def scenario():
        await PostgreSQLGameConfigRepository(database).save(config)
        return await PostgreSQLGameConfigRepository(database).get_current()  # nouveau processus

    assert asyncio.run(scenario()) == config


def test_a_game_action_only_rewrites_the_night_row_and_the_current_game_table(database: Database) -> None:
    repository = PostgreSQLGameConfigRepository(database)
    config = _fair_price_in_progress()
    asyncio.run(repository.save(config))

    writes: list[str] = []
    event.listen(database.engine.sync_engine, "before_cursor_execute", lambda _c, _cur, statement, *_: writes.append(statement))
    asyncio.run(repository.save(config.give_fair_price_hint("plus", 0, START_MS + 100).pull_events()[0]))

    tables = sorted({table for statement in writes for table in ["game_nights", *(f"{key}_games" for key in GAME_STATE_TYPES)] if f"INSERT INTO {table} " in statement})
    assert tables == ["fair_price_games", "game_nights"]


def test_each_save_bumps_the_night_revision(database: Database) -> None:
    repository = PostgreSQLGameConfigRepository(database)
    config = _fair_price_in_progress()
    for _ in range(3):
        asyncio.run(repository.save(config))

    async def revision() -> int:
        async with database.session() as session:
            return (await session.get(GameNightModel, "current")).revision

    assert asyncio.run(revision()) == 3


def test_a_game_added_since_the_last_save_starts_from_its_default_state(database: Database) -> None:
    config = _fair_price_in_progress()
    asyncio.run(PostgreSQLGameConfigRepository(database).save(config))

    async def drop_and_reload():
        async with database.session() as session:
            await session.execute(text("DELETE FROM golden_family_games"))
        return await PostgreSQLGameConfigRepository(database).get_current()

    reloaded = asyncio.run(drop_and_reload())
    assert reloaded.session.golden_family == type(config.session.golden_family)()
    assert reloaded.session.fair_price == config.session.fair_price


def test_a_development_database_imports_its_former_single_document_once(database: Database) -> None:
    config = _fair_price_in_progress()
    payload = json.dumps(game_config_to_payload(config))

    async def scenario():
        async with database.session() as session:
            await session.execute(text("CREATE TABLE game_config_state (aggregate_key VARCHAR(50), payload JSON)"))
            await session.execute(text("INSERT INTO game_config_state VALUES ('current', :payload)"), {"payload": payload})
        imported = await PostgreSQLGameConfigRepository(database).get_current()
        async with database.session() as session:
            legacy_rows = (await session.execute(text("SELECT count(*) FROM game_config_state"))).scalar_one()
            night_rows = (await session.execute(text("SELECT count(*) FROM game_nights"))).scalar_one()
        return imported, legacy_rows, night_rows

    imported, legacy_rows, night_rows = asyncio.run(scenario())
    assert imported == config and night_rows == 1
    assert legacy_rows == 1  # l'ancien document reste en place


def test_migration_0003_moves_the_single_document_into_the_tables_and_back() -> None:
    config = _fair_price_in_progress()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "migrated.db"
        alembic = Config(str(BACK_DIR / "alembic.ini"))
        alembic.attributes.update(database_url=f"sqlite+aiosqlite:///{path}", configure_logging=False)
        command.upgrade(alembic, "0002")
        engine = create_engine(f"sqlite:///{path}")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO game_config_state (aggregate_key, payload, updated_at, revision, checksum, source, notes) "
                    "VALUES ('current', :payload, '2026-11-08', 41, 'x', 'api', '')"
                ),
                {"payload": json.dumps(game_config_to_payload(config))},
            )

        command.upgrade(alembic, "head")
        migrated_db = Database(f"sqlite+aiosqlite:///{path}")
        migrated = asyncio.run(PostgreSQLGameConfigRepository(migrated_db).get_current())
        asyncio.run(migrated_db.dispose())
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT revision FROM game_nights")).scalar_one()
            game_rows = connection.execute(text("SELECT count(*) FROM fair_price_games")).scalar_one()
        assert migrated == config and revision == 41 and game_rows == 1

        command.downgrade(alembic, "0002")
        with engine.connect() as connection:
            restored = json.loads(connection.execute(text("SELECT payload FROM game_config_state")).scalar_one())
        engine.dispose()
        assert game_config_from_payload(restored) == config
