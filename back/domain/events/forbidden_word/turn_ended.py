from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class TurnEnded(DomainEvent):
    name: ClassVar[str] = "forbidden_word.turn_ended"
    team: str
    found_count: int
