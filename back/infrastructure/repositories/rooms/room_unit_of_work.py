from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from application.rooms.room_unit_of_work import RoomUnitOfWork
from infrastructure.database.database import Database
from infrastructure.database.outbox.sql_outbox import SqlOutbox
from infrastructure.database.rate_limiting.sql_attempt_counter import SqlAttemptCounter
from infrastructure.database.sql_unit_of_work import SqlUnitOfWorkSession
from infrastructure.repositories.rooms.postgresql_room_repository import PostgreSQLRoomRepository


class SqlRoomUnitOfWork(SqlUnitOfWorkSession, RoomUnitOfWork):
    """Salon, outbox et compteurs dans une même transaction : un événement n'existe que si l'écriture a eu lieu."""

    def __init__(self, database: Database, attempt_secret: bytes) -> None:
        super().__init__(database)
        self._attempt_secret = attempt_secret

    def _bind(self, session: AsyncSession) -> None:
        self.rooms = PostgreSQLRoomRepository(session)
        self.outbox = SqlOutbox(session)
        self.attempts = SqlAttemptCounter(session, self._attempt_secret)
