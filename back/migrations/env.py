from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from infrastructure.config import Settings
from infrastructure.database import (
    models,  # noqa: F401  (enregistre les tables sur Base.metadata)
)
from infrastructure.database.database import Base

config = context.config
if config.config_file_name and config.attributes.get("configure_logging", True):
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def _database_url() -> str:
    # Une URL passée par le code (tests) prime ; sinon celle de l'application.
    return config.attributes.get("database_url") or Settings().database_url


def _configure(**options: object) -> None:
    context.configure(target_metadata=target_metadata, compare_type=True, **options)


def _run_with(connection: Connection) -> None:
    # SQLite ne sait pas modifier une table en place : Alembic la recopie (« batch »).
    _configure(connection=connection, render_as_batch=connection.dialect.name == "sqlite")
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = create_async_engine(_database_url())
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_with)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    _configure(url=_database_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(_run_online())
