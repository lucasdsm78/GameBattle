from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class VanishedWordRevealed(DomainEvent):
    name: ClassVar[str] = "vanishing_word.word_revealed"
    word: str
    found_by: Optional[str]
