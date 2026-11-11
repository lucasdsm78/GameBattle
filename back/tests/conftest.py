from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from infrastructure.database.database import Database


@pytest.fixture
def sqlite_database() -> Iterator[Database]:
    with tempfile.TemporaryDirectory() as directory:
        database = Database(f"sqlite+aiosqlite:///{Path(directory) / 'gamebattle.db'}")
        asyncio.run(database.create_schema())
        yield database
        asyncio.run(database.dispose())
