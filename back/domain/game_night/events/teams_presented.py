from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class TeamsPresented(DomainEvent):

    name: ClassVar[str] = "game_night.teams_presented"
    teams: tuple[str, ...]
