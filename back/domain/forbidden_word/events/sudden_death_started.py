from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class SuddenDeathStarted(DomainEvent):
    name: ClassVar[str] = "forbidden_word.sudden_death_started"
    round_number: int
    teams: tuple[str, ...]
