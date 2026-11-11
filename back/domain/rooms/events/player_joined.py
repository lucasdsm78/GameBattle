from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class PlayerJoined(DomainEvent):
    """Un joueur est entré dans le salon."""

    name: ClassVar[str] = "room.player_joined"
    pseudo: str
    team: str
