from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import asdict
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.shared.outbox import Outbox
from domain.shared.events.domain_event import DomainEvent
from infrastructure.database.outbox.outbox_event_model import OutboxEventModel


class SqlOutbox(Outbox):
    """Écrit les événements dans la transaction de l'unité de travail : validés ou annulés avec l'agrégat."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, stream: str, events: Sequence[DomainEvent], audience: Optional[str] = None) -> None:
        now_ms = int(time.time() * 1000)
        self._session.add_all(
            OutboxEventModel(stream=stream, event_type=event.name, payload=asdict(event), audience=audience, occurred_at_ms=now_ms)
            for event in events
        )
