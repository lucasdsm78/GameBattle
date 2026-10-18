from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class GameNightFinished(DomainEvent):
    name: ClassVar[str] = "game_night.finished"
    leaders: tuple[str, ...]
