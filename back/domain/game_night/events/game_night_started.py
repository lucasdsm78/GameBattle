from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class GameNightStarted(DomainEvent):
    name: ClassVar[str] = "game_night.started"
    total_rounds: int
