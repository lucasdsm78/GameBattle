from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class FamilyBoardRevealed(DomainEvent):
    name: ClassVar[str] = "golden_family.board_revealed"
    question_number: int
