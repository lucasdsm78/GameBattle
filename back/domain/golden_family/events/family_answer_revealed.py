from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class FamilyAnswerRevealed(DomainEvent):
    name: ClassVar[str] = "golden_family.answer_revealed"
    text: str
    points: int
    team: str
