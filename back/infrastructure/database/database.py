from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str) -> None:
        self._engine = create_async_engine(url, pool_pre_ping=True)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False, autoflush=False)

    async def create_schema(self) -> None:
        from infrastructure.database import (
            all_models,  # noqa: F401  (enregistre toutes les tables sur Base.metadata)
        )

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self._engine.dispose()

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def dialect_name(self) -> str:
        return self._engine.dialect.name

    async def connect(self) -> AsyncConnection:
        """Connexion dédiée, hors des sessions : pour un verrou tenu toute la vie du processus."""
        return await self._engine.connect()

    def new_session(self) -> AsyncSession:
        """Session sans transaction automatique : c'est l'unité de travail qui valide ou annule."""
        return self._sessions()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Transaction : validée en sortie normale, annulée sur exception."""
        async with self._sessions() as session, session.begin():
            yield session
