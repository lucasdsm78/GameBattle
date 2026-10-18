from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class TeamDisqualified(DomainEvent):
    name: ClassVar[str] = "memory.team_disqualified"
    team: str
