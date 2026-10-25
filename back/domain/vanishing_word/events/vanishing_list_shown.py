from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class VanishingListShown(DomainEvent):
    name: ClassVar[str] = "vanishing_word.list_shown"
    round_number: int
