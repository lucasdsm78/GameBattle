from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class PriceHintGiven(DomainEvent):
    """« C'est plus » ou « c'est moins » : le prix lui-même reste secret."""

    name: ClassVar[str] = "fair_price.hint_given"
    team: str
    direction: str
