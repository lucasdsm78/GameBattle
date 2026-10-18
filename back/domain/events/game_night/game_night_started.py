from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class GameNightStarted(DomainEvent):
    name: ClassVar[str] = "game_night.started"
    total_rounds: int
