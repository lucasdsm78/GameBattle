from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class MancheStarted(DomainEvent):
    name: ClassVar[str] = "manche.started"
    number: int
    game_key: str
