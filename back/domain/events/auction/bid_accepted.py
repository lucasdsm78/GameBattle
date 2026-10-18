from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class BidAccepted(DomainEvent):
    name: ClassVar[str] = "auction.bid_accepted"
    team: str
    target_count: int
