from __future__ import annotations

import asyncio
import json
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from support import started_config

from domain.fair_price.models.fair_price_state import FairPriceState
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from exceptions import ConcurrentModificationError
from infrastructure.database import all_models  # noqa: F401  (toutes les tables)
from infrastructure.database.database import Database
from infrastructure.database.game_sessions.game_session_model import GameSessionModel
from infrastructure.database.games.fair_price.fair_price_mapper import FairPriceMapper
from infrastructure.repositories.game_night.cached_game_config import (
    CachedGameConfigRepository,
)
from infrastructure.repositories.game_night.game_config_mapper import (
    common_session_fields,
    game_config_from_payload,
    game_config_to_payload,
    join_payload,
    split_payload,
)
from infrastructure.repositories.game_night.postgresql_game_config import (
    PostgreSQLGameConfigRepository,
)

BACK_DIR = Path(__file__).resolve().parents[1]
START_MS = 1_000
GAME_TABLES = [f"{key}_games" for key in GAME_STATE_TYPES]


def _fair_price_in_progress():
    config = started_config("fair_price").pull_events()[0]
    return config.start_fair_price_turn(START_MS).pull_events()[0]


def _hinted(config):
    return config.give_fair_price_hint("plus", config.session.fair_price.proposals, START_MS + 100).pull_events()[0]


@pytest.fixture
def database() -> Iterator[Database]:
    with tempfile.TemporaryDirectory() as directory:
        db = Database(f"sqlite+aiosqlite:///{Path(directory) / 'sessions.db'}")
        asyncio.run(db.create_schema())
        yield db
        asyncio.run(db.dispose())


async def _scalar(database: Database, sql: str) -> Any:
    async with database.session() as session:
        return (await session.execute(text(sql))).scalar_one()


# --- Forme en base ---


def test_the_common_table_has_a_column_per_shared_lifecycle_field() -> None:
    columns = {column.name for column in GameSessionModel.__table__.columns}

    # Un champ ajouté à `GameSession` sans colonne (ni migration) fait échouer ce test.
    assert {"session_updated_at" if name == "updated_at" else name for name in common_session_fields()} <= columns
    assert {"version", "created_at", "saved_at", "active_game_key"} <= columns


def test_split_and_join_are_inverse_and_expose_the_active_game() -> None:
    payload = game_config_to_payload(_fair_price_in_progress())
    record = split_payload(payload)

    assert join_payload(record) == payload
    assert record.common["active_game_key"] == "fair_price"


def test_a_session_round_trips_through_its_tables(database: Database) -> None:
    config = _fair_price_in_progress()

    async def scenario():
        await PostgreSQLGameConfigRepository(database).save(config)
        return await PostgreSQLGameConfigRepository(database).get_current()  # nouveau processus

    assert asyncio.run(scenario()) == config


def test_a_game_action_only_rewrites_the_common_row_and_the_current_game(database: Database) -> None:
    repository = PostgreSQLGameConfigRepository(database)
    config = _fair_price_in_progress()
    asyncio.run(repository.save(config))

    writes: list[str] = []
    event.listen(database.engine.sync_engine, "before_cursor_execute", lambda _c, _cur, statement, *_: writes.append(statement))
    asyncio.run(repository.save(_hinted(config)))

    written = sorted({table for statement in writes for table in ["game_sessions", *GAME_TABLES] if f"UPDATE {table} " in statement or f"INSERT INTO {table} " in statement})
    assert written == ["fair_price_games", "game_sessions"]


def test_versions_count_the_writes_of_each_row(database: Database) -> None:
    repository = PostgreSQLGameConfigRepository(database)
    config = _fair_price_in_progress()
    asyncio.run(repository.save(config))
    asyncio.run(repository.save(config))  # rien de changé dans les jeux
    asyncio.run(repository.save(_hinted(config)))

    assert asyncio.run(_scalar(database, "SELECT version FROM game_sessions")) == 3
    assert asyncio.run(_scalar(database, "SELECT version FROM fair_price_games")) == 2
    assert asyncio.run(_scalar(database, "SELECT version FROM blindtest_games")) == 1


def test_a_game_added_since_the_last_save_starts_from_its_default_state(database: Database) -> None:
    config = _fair_price_in_progress()
    asyncio.run(PostgreSQLGameConfigRepository(database).save(config))

    async def drop_and_reload():
        async with database.session() as session:
            await session.execute(text("DELETE FROM golden_family_games"))
        repository = PostgreSQLGameConfigRepository(database)
        reloaded = await repository.get_current()
        await repository.save(reloaded)  # la ligne manquante est recréée
        return reloaded

    reloaded = asyncio.run(drop_and_reload())
    assert reloaded.session.golden_family == type(config.session.golden_family)()
    assert asyncio.run(_scalar(database, "SELECT count(*) FROM golden_family_games")) == 1


# --- Verrou optimiste ---


def test_a_concurrent_write_is_refused_instead_of_overwriting(database: Database) -> None:
    config = _fair_price_in_progress()
    asyncio.run(PostgreSQLGameConfigRepository(database).save(config))
    first, second = PostgreSQLGameConfigRepository(database), PostgreSQLGameConfigRepository(database)
    asyncio.run(first.get_current())
    asyncio.run(second.get_current())

    winner = _hinted(config)
    asyncio.run(first.save(winner))
    with pytest.raises(ConcurrentModificationError, match="modifiée en même temps"):
        asyncio.run(second.save(config.give_fair_price_hint("moins", 0, START_MS + 200).pull_events()[0]))

    assert asyncio.run(PostgreSQLGameConfigRepository(database).get_current()) == winner  # rien n'a été écrasé
    asyncio.run(second.get_current())  # après relecture, l'écriture repasse
    asyncio.run(second.save(_hinted(winner)))


def test_a_conflict_on_a_game_row_rolls_back_the_whole_write(database: Database) -> None:
    repository = PostgreSQLGameConfigRepository(database)
    config = _fair_price_in_progress()
    asyncio.run(repository.save(config))

    async def bump_fair_price_elsewhere() -> None:
        async with database.session() as session:
            await session.execute(text("UPDATE fair_price_games SET version = version + 1"))

    asyncio.run(bump_fair_price_elsewhere())
    with pytest.raises(ConcurrentModificationError):
        asyncio.run(repository.save(_hinted(config)))
    assert asyncio.run(_scalar(database, "SELECT version FROM game_sessions")) == 1  # la ligne commune n'a pas bougé


def test_the_cache_reloads_after_a_conflict(database: Database) -> None:
    config = _fair_price_in_progress()
    asyncio.run(PostgreSQLGameConfigRepository(database).save(config))
    cached = CachedGameConfigRepository(PostgreSQLGameConfigRepository(database))
    asyncio.run(cached.get_current())
    other_writer = PostgreSQLGameConfigRepository(database)
    asyncio.run(other_writer.get_current())
    winner = _hinted(config)
    asyncio.run(other_writer.save(winner))

    with pytest.raises(ConcurrentModificationError):
        asyncio.run(cached.save(config.give_fair_price_hint("moins", 0, START_MS + 200).pull_events()[0]))
    assert asyncio.run(cached.get_current()) == winner


# --- Documents JSONB versionnés ---


class FairPriceMapperV3(FairPriceMapper):
    schema_version = 3
    migrations = {
        1: lambda document: {**document, "proposals": document.get("proposals", 0) + 10},
        2: lambda document: {**document, "proposals": document["proposals"] * 2},
    }


def test_an_old_document_is_migrated_step_by_step_to_the_current_version() -> None:
    document = {"phase": "idle", "proposals": 1}

    assert FairPriceMapperV3().to_state(document, schema_version=1, teams=[]).proposals == 22  # (1 + 10) × 2
    assert FairPriceMapperV3().to_state(document, schema_version=2, teams=[]).proposals == 2
    assert isinstance(FairPriceMapperV3().to_state(document, schema_version=3, teams=[]), FairPriceState)


def test_a_document_from_newer_code_is_refused() -> None:
    with pytest.raises(ValueError, match="plus récent"):
        FairPriceMapper().to_state({"phase": "idle"}, schema_version=2, teams=[])


def test_rows_are_written_at_the_current_schema_version(database: Database) -> None:
    asyncio.run(PostgreSQLGameConfigRepository(database).save(_fair_price_in_progress()))

    assert asyncio.run(_scalar(database, "SELECT schema_version FROM fair_price_games")) == FairPriceMapper.schema_version


# --- Reprise des données ---


def test_a_development_database_imports_its_former_single_document_once(database: Database) -> None:
    config = _fair_price_in_progress()

    async def scenario():
        async with database.session() as session:
            await session.execute(text("CREATE TABLE game_config_state (aggregate_key VARCHAR(50), payload JSON)"))
            await session.execute(text("INSERT INTO game_config_state VALUES ('current', :payload)"), {"payload": json.dumps(game_config_to_payload(config))})
        return await PostgreSQLGameConfigRepository(database).get_current()

    assert asyncio.run(scenario()) == config
    assert asyncio.run(_scalar(database, "SELECT count(*) FROM game_config_state")) == 1  # l'ancien document reste


def _alembic(path: Path) -> Config:
    config = Config(str(BACK_DIR / "alembic.ini"))
    config.attributes.update(database_url=f"sqlite+aiosqlite:///{path}", configure_logging=False)
    return config


def test_migrations_move_the_single_document_into_the_session_tables_and_back() -> None:
    config = _fair_price_in_progress()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "migrated.db"
        alembic = _alembic(path)
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

        command.upgrade(alembic, "0003")  # document unique -> game_nights + tables de jeu
        with engine.connect() as connection:
            assert connection.execute(text("SELECT revision FROM game_nights")).scalar_one() == 41

        command.upgrade(alembic, "head")  # 0004 : game_sessions, versions, jeu en cours
        with engine.connect() as connection:
            row = connection.execute(text("SELECT version, active_game_key, created_at FROM game_sessions")).one()
            game_version = connection.execute(text("SELECT version FROM fair_price_games WHERE session_id = 'current'")).scalar_one()
        assert row.version == 41 and row.active_game_key == "fair_price" and row.created_at is not None and game_version == 1
        migrated_db = Database(f"sqlite+aiosqlite:///{path}")
        repository = PostgreSQLGameConfigRepository(migrated_db)
        assert asyncio.run(repository.get_current()) == config
        hinted = _hinted(config)
        asyncio.run(repository.save(hinted))  # le verrou optimiste part des versions migrées
        asyncio.run(migrated_db.dispose())

        command.downgrade(alembic, "0002")
        with engine.connect() as connection:
            restored = json.loads(connection.execute(text("SELECT payload FROM game_config_state")).scalar_one())
        engine.dispose()
        assert game_config_from_payload(restored) == hinted
