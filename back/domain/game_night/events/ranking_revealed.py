from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class RankingRevealed(DomainEvent):
    name: ClassVar[str] = "ranking.revealed"
    team: str
    rank: int
    manches_won: int
