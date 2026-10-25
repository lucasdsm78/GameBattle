from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class CountryAnnounced(DomainEvent):
    """Un nouveau pays est annoncé ; son drapeau reste secret jusqu'à sa révélation."""

    name: ClassVar[str] = "right_flag.country_announced"
    round_number: int
    country: str
