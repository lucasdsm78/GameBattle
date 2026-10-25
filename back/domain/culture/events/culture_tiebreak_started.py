from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class CultureTiebreakStarted(DomainEvent):
    name: ClassVar[str] = "culture.tiebreak_started"
    teams: tuple[str, ...]
