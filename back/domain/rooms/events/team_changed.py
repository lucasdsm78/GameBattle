from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class TeamChanged(DomainEvent):
    """Un joueur a changé d'équipe (salon privé en équipes)."""

    name: ClassVar[str] = "room.team_changed"
    pseudo: str
    team: str
