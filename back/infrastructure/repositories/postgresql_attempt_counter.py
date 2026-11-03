from __future__ import annotations

from sqlalchemy import case, delete, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from application.accounts.attempt_counter import AttemptCounter, AttemptWindow
from infrastructure.database.models import AuthAttemptModel

_UPSERTS = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}


class PostgreSQLAttemptCounter(AttemptCounter):
    """Fenêtres fixes en base : un seul `INSERT … ON CONFLICT DO UPDATE … RETURNING` par essai, atomique même sous concurrence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def peek(self, key: str, now_ms: int, window_ms: int) -> AttemptWindow:
        row = (
            await self._session.execute(
                select(AuthAttemptModel.window_start_ms, AuthAttemptModel.count).where(AuthAttemptModel.key == key)
            )
        ).first()
        if row is None or now_ms >= row.window_start_ms + window_ms:
            return AttemptWindow(count=0, resets_at_ms=now_ms + window_ms)
        return AttemptWindow(count=row.count, resets_at_ms=row.window_start_ms + window_ms)

    async def hit(self, key: str, now_ms: int, window_ms: int) -> AttemptWindow:
        insert = _UPSERTS[self._session.bind.dialect.name](AuthAttemptModel).values(key=key, window_start_ms=now_ms, count=1)
        expired = AuthAttemptModel.window_start_ms + window_ms <= insert.excluded.window_start_ms
        upsert = insert.on_conflict_do_update(
            index_elements=[AuthAttemptModel.key],
            set_={
                "count": case((expired, 1), else_=AuthAttemptModel.count + 1),
                "window_start_ms": case((expired, insert.excluded.window_start_ms), else_=AuthAttemptModel.window_start_ms),
            },
        ).returning(AuthAttemptModel.window_start_ms, AuthAttemptModel.count)
        row = (await self._session.execute(upsert)).one()
        return AttemptWindow(count=row.count, resets_at_ms=row.window_start_ms + window_ms)

    async def reset(self, key: str) -> None:
        await self._session.execute(delete(AuthAttemptModel).where(AuthAttemptModel.key == key))

    async def purge(self, started_before_ms: int) -> None:
        await self._session.execute(delete(AuthAttemptModel).where(AuthAttemptModel.window_start_ms < started_before_ms))
