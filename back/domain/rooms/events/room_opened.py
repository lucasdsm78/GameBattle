from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class RoomOpened(DomainEvent):
    """Un salon vient d'ouvrir."""

    name: ClassVar[str] = "room.opened"
    visibility: str
    format: str
    max_players: int
    host: str
