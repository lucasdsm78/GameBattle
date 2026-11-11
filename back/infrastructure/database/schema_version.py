from __future__ import annotations

from pathlib import Path
from typing import Optional

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection

from infrastructure.config import BASE_DIR
from infrastructure.database.database import Database

ALEMBIC_CONFIG = BASE_DIR / "alembic.ini"


class OutdatedSchemaError(RuntimeError):
    """La base suivie par Alembic est en retard sur le code : on refuse de démarrer plutôt que de créer des tables à moitié."""


def _current_revision(connection: Connection) -> Optional[str]:
    return MigrationContext.configure(connection).get_current_revision()  # `None` : base jamais migrée


def head_revision(config_path: Path = ALEMBIC_CONFIG) -> Optional[str]:
    return ScriptDirectory.from_config(Config(str(config_path))).get_current_head()


async def ensure_schema_is_current(database: Database, config_path: Path = ALEMBIC_CONFIG) -> None:
    """Au démarrage : une base suivie par Alembic doit être à la dernière migration.

    Sinon, en développement, la création automatique des tables manquantes ajouterait des tables au schéma du
    moment, que les migrations ne pourraient plus appliquer ensuite. Une base jamais migrée (tests, SQLite tout
    neuf) n'est pas concernée.
    """
    async with database.engine.connect() as connection:
        current = await connection.run_sync(_current_revision)
    head = head_revision(config_path)
    if current is not None and current != head:
        raise OutdatedSchemaError(
            f"La base est à la migration {current}, le code attend {head}. "
            "Mets-la à jour avant de démarrer : cd back && .venv/bin/alembic upgrade head"
        )
