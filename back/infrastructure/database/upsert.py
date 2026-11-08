from __future__ import annotations

from typing import Any

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

# `INSERT … ON CONFLICT DO UPDATE` existe sous la même forme dans les deux moteurs : PostgreSQL en production,
# SQLite pour les tests.
_INSERTS = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}


def upsert_insert(session: AsyncSession, model: type[Any]) -> Any:
    """`INSERT` du dialecte de la session, qui expose `on_conflict_do_update` et `excluded`."""
    return _INSERTS[session.bind.dialect.name](model)
