from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class AnswerJudged(DomainEvent):
    name: ClassVar[str] = "answer.judged"
    game_key: str
    team: str
    correct: bool
