from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class ChronoRoundStarted(DomainEvent):
    name: ClassVar[str] = "stopchrono.round_started"
    round_number: int
    target_seconds: int
    first_team: str
