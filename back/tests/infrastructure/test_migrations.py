from __future__ import annotations

import tempfile
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine
from support import BACK_DIR

from infrastructure.database import (
    all_models,  # noqa: F401  (toutes les tables, pour comparer les migrations)
)
from infrastructure.database.database import Base


def test_migrations_build_exactly_the_schema_of_the_models() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "migrated.db"
        config = Config(str(BACK_DIR / "alembic.ini"))
        config.attributes.update(database_url=f"sqlite+aiosqlite:///{path}", configure_logging=False)
        command.upgrade(config, "head")

        engine = create_engine(f"sqlite:///{path}")
        with engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)
        engine.dispose()
        assert differences == []
        command.downgrade(config, "base")
