from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class GameNightStarted(DomainEvent):
    name: ClassVar[str] = "game_night.started"
    total_rounds: int


@dataclass(frozen=True, slots=True)
class MancheStarted(DomainEvent):
    name: ClassVar[str] = "manche.started"
    number: int
    game_key: str


@dataclass(frozen=True, slots=True)
class MancheFinished(DomainEvent):
    name: ClassVar[str] = "manche.finished"
    number: int
    game_key: str
    winner: str


@dataclass(frozen=True, slots=True)
class GameNightFinished(DomainEvent):
    name: ClassVar[str] = "game_night.finished"
    leaders: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RankingRevealed(DomainEvent):
    name: ClassVar[str] = "ranking.revealed"
    team: str
    rank: int
    manches_won: int
