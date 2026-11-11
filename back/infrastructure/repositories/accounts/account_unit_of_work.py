from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from application.accounts.account_unit_of_work import AccountUnitOfWork
from infrastructure.database.database import Database
from infrastructure.database.rate_limiting.sql_attempt_counter import SqlAttemptCounter
from infrastructure.database.sql_unit_of_work import SqlUnitOfWorkSession
from infrastructure.repositories.accounts.postgresql_player_account_repository import (
    PostgreSQLPlayerAccountRepository,
)
from infrastructure.repositories.accounts.postgresql_player_session_repository import (
    PostgreSQLPlayerSessionRepository,
)


class SqlAccountUnitOfWork(SqlUnitOfWorkSession, AccountUnitOfWork):
    """Comptes, sessions et compteurs partagent une même session SQLAlchemy, donc une même transaction."""

    def __init__(self, database: Database, attempt_secret: bytes) -> None:
        super().__init__(database)
        self._attempt_secret = attempt_secret

    def _bind(self, session: AsyncSession) -> None:
        self.accounts = PostgreSQLPlayerAccountRepository(session)
        self.sessions = PostgreSQLPlayerSessionRepository(session)
        self.attempts = SqlAttemptCounter(session, self._attempt_secret)
