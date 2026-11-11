from __future__ import annotations

from abc import abstractmethod
from types import TracebackType
from typing import Optional, Self

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.database import Database


class SqlUnitOfWorkSession:
    """Socle des unités de travail SQL : une session SQLAlchemy par opération, donc une transaction.

    Sortir du bloc annule ce qui n'a pas été validé ; `commit()` valide, et l'on peut continuer à lire ensuite.
    Chaque module branche ses dépôts sur la session dans `_bind`.
    """

    def __init__(self, database: Database) -> None:
        self._database = database
        self._session: Optional[AsyncSession] = None

    @abstractmethod
    def _bind(self, session: AsyncSession) -> None: ...

    async def __aenter__(self) -> Self:
        self._session = self._database.new_session()
        self._bind(self._session)
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        assert self._session is not None
        try:
            await self._session.rollback()  # sans effet sur ce qui a déjà été validé
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()
