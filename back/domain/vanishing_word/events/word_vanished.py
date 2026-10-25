from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class WordVanished(DomainEvent):
    """Un mot vient de disparaître ; lequel reste secret jusqu'à sa révélation."""

    name: ClassVar[str] = "vanishing_word.word_vanished"
    round_number: int
