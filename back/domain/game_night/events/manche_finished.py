from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class MancheFinished(DomainEvent):
    name: ClassVar[str] = "manche.finished"
    number: int
    game_key: str
    winner: str
