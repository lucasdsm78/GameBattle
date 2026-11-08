from __future__ import annotations

from types import TracebackType
from typing import Optional, Self

from sqlalchemy.ext.asyncio import AsyncSession

from application.accounts.account_unit_of_work import AccountUnitOfWork
from infrastructure.database.database import Database
from infrastructure.repositories.postgresql_player_account_repository import (
    PostgreSQLPlayerAccountRepository,
)
from infrastructure.repositories.postgresql_player_session_repository import (
    PostgreSQLPlayerSessionRepository,
)
from infrastructure.repositories.sql_attempt_counter import SqlAttemptCounter


class SqlAccountUnitOfWork(AccountUnitOfWork):
    """Comptes, sessions et compteurs partagent une même session SQLAlchemy, donc une même transaction."""

    def __init__(self, database: Database, attempt_secret: bytes) -> None:
        self._database = database
        self._attempt_secret = attempt_secret
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> Self:
        self._session = self._database.new_session()
        self.accounts = PostgreSQLPlayerAccountRepository(self._session)
        self.sessions = PostgreSQLPlayerSessionRepository(self._session)
        self.attempts = SqlAttemptCounter(self._session, self._attempt_secret)
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
