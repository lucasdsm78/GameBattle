from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ForbiddenWordCard:
    id: str
    word: str
    forbidden_words: list[str]


@dataclass(slots=True)
class ForbiddenWordTurn:
    team: str
    found_words: list[str] = field(default_factory=list)
    skipped_words: list[str] = field(default_factory=list)
    round: int = 0
