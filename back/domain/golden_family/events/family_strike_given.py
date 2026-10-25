from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class FamilyStrikeGiven(DomainEvent):
    name: ClassVar[str] = "golden_family.strike_given"
    team: str
    strikes: int
