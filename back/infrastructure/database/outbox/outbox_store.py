from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import delete, select, update

from infrastructure.database.database import Database
from infrastructure.database.outbox.outbox_event_model import OutboxEventModel


@dataclass(frozen=True, slots=True)
class PendingEvent:
    id: int
    stream: str
    event_type: str
    payload: dict[str, Any]
    audience: Optional[str]


class OutboxStore:
    """Côté relais : lire les événements pas encore publiés, dans l'ordre, puis les marquer publiés."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def pending(self, limit: int) -> list[PendingEvent]:
        model = OutboxEventModel
        async with self._database.session() as session:
            rows = (
                await session.execute(
                    select(model.id, model.stream, model.event_type, model.payload, model.audience)
                    .where(model.published_at_ms.is_(None))
                    .order_by(model.id)
                    .limit(limit)
                )
            ).all()
        return [PendingEvent(row.id, row.stream, row.event_type, row.payload, row.audience) for row in rows]

    async def mark_published(self, event_ids: list[int], now_ms: int) -> None:
        if not event_ids:
            return
        async with self._database.session() as session:
            await session.execute(update(OutboxEventModel).where(OutboxEventModel.id.in_(event_ids)).values(published_at_ms=now_ms))

    async def purge_published(self, published_before_ms: int) -> None:
        async with self._database.session() as session:
            await session.execute(delete(OutboxEventModel).where(OutboxEventModel.published_at_ms < published_before_ms))
