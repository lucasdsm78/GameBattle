from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class RoomClosed(DomainEvent):
    """Le salon est fermé (vide ou inactif)."""

    name: ClassVar[str] = "room.closed"
    reason: str
