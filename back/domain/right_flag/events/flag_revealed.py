from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class FlagRevealed(DomainEvent):
    name: ClassVar[str] = "right_flag.flag_revealed"
    country_code: str
    found_by: Optional[str]
