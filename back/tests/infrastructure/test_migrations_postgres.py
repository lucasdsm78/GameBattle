"""Migrations sur un vrai PostgreSQL : JSONB, renommages, clés étrangères, verrou optimiste.

Lancé quand `GAMEBATTLE_TEST_POSTGRES_URL` désigne un serveur jetable (`scripts/test-migrations-postgres.sh` en
démarre un dans Docker) ; ignoré sinon. Deux bases sont créées puis supprimées sur ce serveur : l'une migrée
depuis 0002 avec des données réelles, l'autre construite directement depuis les modèles, comme référence.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from support import BACK_DIR, started_config

from domain.game_night.models.game_registry import GAME_STATE_TYPES
from exceptions import ConcurrentModificationError
from infrastructure.database import all_models  # noqa: F401  (toutes les tables)
from infrastructure.database.database import Base, Database
from infrastructure.repositories.game_night.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from infrastructure.repositories.game_night.postgresql_game_config import (
    PostgreSQLGameConfigRepository,
)

SERVER_URL = os.environ.get("GAMEBATTLE_TEST_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(not SERVER_URL, reason="GAMEBATTLE_TEST_POSTGRES_URL non défini : pas de PostgreSQL de test")
GAME_TABLES = [f"{key}_games" for key in GAME_STATE_TYPES]
START_MS = 1_000

CONSTRAINTS = """
    SELECT conrelid::regclass::text AS table_name, conname, pg_get_constraintdef(oid) AS definition
    FROM pg_constraint
    WHERE connamespace = 'public'::regnamespace AND conrelid::regclass::text <> 'alembic_version'
    ORDER BY 1, 2
"""
INDEXES = "SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename <> 'alembic_version' ORDER BY 1, 2"
COLUMNS = """
    SELECT table_name, column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name <> 'alembic_version'
    ORDER BY 1, 2
"""


def _url(database: str) -> str:
    return make_url(SERVER_URL).set(database=database).render_as_string(hide_password=False)


async def _admin(statement: str) -> None:
    engine = create_async_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as connection:
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


async def _query(url: str, sql: str, **parameters: Any) -> list[tuple[Any, ...]]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            return [tuple(row) for row in (await connection.execute(text(sql), parameters)).all()]
    finally:
        await engine.dispose()


async def _execute(url: str, sql: str, **parameters: Any) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(sql), parameters)
    finally:
        await engine.dispose()


@pytest.fixture
def databases() -> Iterator[tuple[str, str]]:
    """Deux bases jetables : (migrée, référence construite depuis les modèles)."""
    suffix = uuid.uuid4().hex[:8]
    names = (f"gb_migrated_{suffix}", f"gb_reference_{suffix}")
    for name in names:
        asyncio.run(_admin(f'CREATE DATABASE "{name}"'))
    try:
        yield tuple(_url(name) for name in names)  # type: ignore[misc]
    finally:
        for name in names:
            asyncio.run(_admin(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


def _alembic(url: str) -> Config:
    config = Config(str(BACK_DIR / "alembic.ini"))
    config.attributes.update(database_url=url, configure_logging=False)
    return config


def _game_in_progress():
    return started_config("fair_price").pull_events()[0].start_fair_price_turn(START_MS).pull_events()[0]


def _insert_legacy_document(url: str, config: Any) -> None:
    asyncio.run(
        _execute(
            url,
            "INSERT INTO game_config_state (aggregate_key, payload, updated_at, revision, checksum, source, notes) "
            "VALUES ('current', CAST(:payload AS JSON), now(), 41, 'x', 'api', '')",
            payload=json.dumps(game_config_to_payload(config)),
        )
    )


def test_migrations_from_0002_build_the_same_schema_as_the_models(databases: tuple[str, str]) -> None:
    migrated, reference = databases
    command.upgrade(_alembic(migrated), "0002")
    _insert_legacy_document(migrated, _game_in_progress())
    command.upgrade(_alembic(migrated), "head")

    async def build_reference() -> None:
        database = Database(reference)
        await database.create_schema()
        await database.dispose()

    asyncio.run(build_reference())
    for catalog in (CONSTRAINTS, INDEXES, COLUMNS):
        assert asyncio.run(_query(migrated, catalog)) == asyncio.run(_query(reference, catalog))

    async def differences() -> list[Any]:
        engine = create_async_engine(migrated)
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(
                    lambda sync: compare_metadata(MigrationContext.configure(sync, opts={"compare_type": True}), Base.metadata)
                )
        finally:
            await engine.dispose()

    assert asyncio.run(differences()) == []


def test_foreign_keys_follow_the_rename_and_cascade(databases: tuple[str, str]) -> None:
    migrated, _ = databases
    command.upgrade(_alembic(migrated), "0002")
    _insert_legacy_document(migrated, _game_in_progress())
    command.upgrade(_alembic(migrated), "head")

    foreign_keys = asyncio.run(
        _query(
            migrated,
            "SELECT conrelid::regclass::text, conname, confrelid::regclass::text, confdeltype::text FROM pg_constraint "
            "WHERE contype = 'f' AND conrelid::regclass::text LIKE '%\\_games' ORDER BY 1",
        )
    )
    assert [row[0] for row in foreign_keys] == sorted(GAME_TABLES)
    assert all(row[1] == f"{row[0]}_session_id_fkey" and row[2] == "game_sessions" and row[3] == "c" for row in foreign_keys)
    assert asyncio.run(_query(migrated, "SELECT count(*) FROM fair_price_games")) == [(1,)]

    asyncio.run(_execute(migrated, "DELETE FROM game_sessions WHERE id = 'current'"))
    assert asyncio.run(_query(migrated, "SELECT count(*) FROM fair_price_games")) == [(0,)]  # ON DELETE CASCADE


def test_data_survive_the_round_trip_and_the_lock_works_on_postgresql(databases: tuple[str, str]) -> None:
    migrated, _ = databases
    config = _game_in_progress()
    command.upgrade(_alembic(migrated), "0002")
    _insert_legacy_document(migrated, config)
    command.upgrade(_alembic(migrated), "head")

    hinted = config.give_fair_price_hint("plus", 0, START_MS + 100).pull_events()[0]

    async def play() -> None:
        database = Database(migrated)
        try:
            first, second = PostgreSQLGameConfigRepository(database), PostgreSQLGameConfigRepository(database)
            assert await first.get_current() == config
            await second.get_current()
            await first.save(hinted)
            with pytest.raises(ConcurrentModificationError):  # `rowcount` de PostgreSQL : la course est détectée
                await second.save(config.give_fair_price_hint("moins", 0, START_MS + 200).pull_events()[0])
            assert await PostgreSQLGameConfigRepository(database).get_current() == hinted
        finally:
            await database.dispose()

    asyncio.run(play())
    assert asyncio.run(_query(migrated, "SELECT version, active_game_key FROM game_sessions")) == [(42, "fair_price")]
    types = dict(asyncio.run(_query(migrated, "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'fair_price_games'")))
    assert types["state"] == "jsonb"

    command.downgrade(_alembic(migrated), "0002")
    (payload,) = asyncio.run(_query(migrated, "SELECT payload::text FROM game_config_state WHERE aggregate_key = 'current'"))[0]
    assert game_config_from_payload(json.loads(payload)) == hinted

    command.upgrade(_alembic(migrated), "head")  # le cycle complet se rejoue sans erreur
    assert asyncio.run(_query(migrated, "SELECT conname FROM pg_constraint WHERE conname = 'game_sessions_pkey'")) == [("game_sessions_pkey",)]
