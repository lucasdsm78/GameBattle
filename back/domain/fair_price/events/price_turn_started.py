from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class PriceTurnStarted(DomainEvent):
    name: ClassVar[str] = "fair_price.turn_started"
    team: str
    item_name: str
