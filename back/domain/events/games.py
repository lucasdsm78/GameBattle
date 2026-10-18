from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent

# --- Communs aux jeux à buzzer


@dataclass(frozen=True, slots=True)
class BuzzerPressed(DomainEvent):
    name: ClassVar[str] = "buzzer.pressed"
    game_key: str
    team: str


@dataclass(frozen=True, slots=True)
class AnswerJudged(DomainEvent):
    name: ClassVar[str] = "answer.judged"
    game_key: str
    team: str
    correct: bool


# --- Stop Chrono


@dataclass(frozen=True, slots=True)
class ChronoStarted(DomainEvent):
    name: ClassVar[str] = "stopchrono.started"
    team: str


@dataclass(frozen=True, slots=True)
class ChronoStopped(DomainEvent):
    name: ClassVar[str] = "stopchrono.stopped"
    team: str
    elapsed_ms: int
    delta_ms: int


# --- La Bombe


@dataclass(frozen=True, slots=True)
class BombeDieRolling(DomainEvent):
    name: ClassVar[str] = "bombe.die_rolling"
    team: str


@dataclass(frozen=True, slots=True)
class BombeArmed(DomainEvent):
    name: ClassVar[str] = "bombe.armed"
    team: str
    die_result: str


@dataclass(frozen=True, slots=True)
class BombePassed(DomainEvent):
    name: ClassVar[str] = "bombe.passed"
    from_team: str
    to_team: str


@dataclass(frozen=True, slots=True)
class BombeExploded(DomainEvent):
    name: ClassVar[str] = "bombe.exploded"
    team: str


# --- Mémoire en chaîne


@dataclass(frozen=True, slots=True)
class ChainRecited(DomainEvent):
    name: ClassVar[str] = "memory.chain_recited"
    team: str


@dataclass(frozen=True, slots=True)
class TeamDisqualified(DomainEvent):
    name: ClassVar[str] = "memory.team_disqualified"
    team: str


# --- Les 7 différences


@dataclass(frozen=True, slots=True)
class DifferenceFound(DomainEvent):
    name: ClassVar[str] = "seven_differences.difference_found"
    team: str
    remaining: int


# --- L’Enchère


@dataclass(frozen=True, slots=True)
class BidAccepted(DomainEvent):
    name: ClassVar[str] = "auction.bid_accepted"
    team: str
    target_count: int


@dataclass(frozen=True, slots=True)
class AuctionResolved(DomainEvent):
    name: ClassVar[str] = "auction.resolved"
    team: str
    target_count: int
    succeeded: bool


# --- Le mot interdit


@dataclass(frozen=True, slots=True)
class TurnStarted(DomainEvent):
    name: ClassVar[str] = "forbidden_word.turn_started"
    team: str


@dataclass(frozen=True, slots=True)
class WordFound(DomainEvent):
    name: ClassVar[str] = "forbidden_word.word_found"
    team: str
    word: str


@dataclass(frozen=True, slots=True)
class WordSkipped(DomainEvent):
    name: ClassVar[str] = "forbidden_word.word_skipped"
    team: str
    word: str


@dataclass(frozen=True, slots=True)
class TurnEnded(DomainEvent):
    name: ClassVar[str] = "forbidden_word.turn_ended"
    team: str
    found_count: int
