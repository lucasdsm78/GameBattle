from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class CultureAnswerRevealed(DomainEvent):
    """Le présentateur révèle la réponse : personne ne marque."""

    name: ClassVar[str] = "culture.answer_revealed"
    question_number: int
