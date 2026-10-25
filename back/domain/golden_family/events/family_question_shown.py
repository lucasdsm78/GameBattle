from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class FamilyQuestionShown(DomainEvent):
    name: ClassVar[str] = "golden_family.question_shown"
    question_number: int
    answer_count: int
