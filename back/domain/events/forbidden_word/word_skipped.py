from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class WordSkipped(DomainEvent):
    name: ClassVar[str] = "forbidden_word.word_skipped"
    team: str
    word: str
