from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class DifferenceFound(DomainEvent):
    name: ClassVar[str] = "seven_differences.difference_found"
    team: str
    remaining: int
