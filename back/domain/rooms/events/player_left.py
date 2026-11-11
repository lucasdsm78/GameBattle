from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class PlayerLeft(DomainEvent):
    """Un joueur a quitté le salon."""

    name: ClassVar[str] = "room.player_left"
    pseudo: str
