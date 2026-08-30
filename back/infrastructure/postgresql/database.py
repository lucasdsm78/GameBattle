from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from infrastructure.config import Settings


class Base(DeclarativeBase):
    pass


_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
_database_url: Optional[str] = None


def configure_database(settings: Settings) -> None:
    global _engine, _session_factory, _database_url
    if _engine is None or _database_url != settings.database_url:
        _engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)
        _database_url = settings.database_url


async def init_database() -> None:
    if _engine is None:
        raise RuntimeError("Database engine not configured.")

    from infrastructure.postgresql.models import GameConfigStateModel

    engine = _engine
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    global _engine, _session_factory, _database_url
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
    _database_url = None


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Session factory not configured.")
    session_factory = _session_factory
    assert session_factory is not None
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()




