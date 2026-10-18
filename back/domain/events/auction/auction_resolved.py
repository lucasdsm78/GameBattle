from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class AuctionResolved(DomainEvent):
    name: ClassVar[str] = "auction.resolved"
    team: str
    target_count: int
    succeeded: bool
