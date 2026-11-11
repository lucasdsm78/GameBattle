from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import text

from infrastructure.database.database import Database
from infrastructure.database.schema_version import OutdatedSchemaError, ensure_schema_is_current, head_revision


def _stamp(database: Database, revision: str) -> None:
    async def write() -> None:
        async with database.engine.begin() as connection:
            await connection.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"))
            await connection.execute(text("DELETE FROM alembic_version"))
            await connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revision})

    asyncio.run(write())


def test_a_base_never_migrated_is_left_alone(sqlite_database: Database) -> None:
    asyncio.run(ensure_schema_is_current(sqlite_database))  # tests, SQLite tout neuf : création automatique des tables


def test_a_base_at_the_last_migration_starts(sqlite_database: Database) -> None:
    _stamp(sqlite_database, head_revision() or "")

    asyncio.run(ensure_schema_is_current(sqlite_database))


def test_a_base_behind_the_code_refuses_to_start_and_says_what_to_run(sqlite_database: Database) -> None:
    _stamp(sqlite_database, "0004")

    with pytest.raises(OutdatedSchemaError) as refused:
        asyncio.run(ensure_schema_is_current(sqlite_database))
    assert "0004" in str(refused.value) and str(head_revision()) in str(refused.value)
    assert "alembic upgrade head" in str(refused.value)
