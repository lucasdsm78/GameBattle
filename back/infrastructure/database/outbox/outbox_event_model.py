from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.database import Base
from infrastructure.database.json_document import JsonDocument

# Entier 64 bits auto-incrémenté sous PostgreSQL ; SQLite n'auto-incrémente que `INTEGER PRIMARY KEY`.
EventId = BigInteger().with_variant(Integer(), "sqlite")


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(EventId, primary_key=True, autoincrement=True)  # ordre de publication
    stream: Mapped[str] = mapped_column(String(80), nullable=False)  # ex. « room:<id> »
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonDocument, nullable=False)
    audience: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)  # compte destinataire d'un événement privé
    occurred_at_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    published_at_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, index=True)
