from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class WordFound(DomainEvent):
    name: ClassVar[str] = "forbidden_word.word_found"
    team: str
    word: str
