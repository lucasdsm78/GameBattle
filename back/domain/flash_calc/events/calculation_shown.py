from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class CalculationShown(DomainEvent):
    name: ClassVar[str] = "flash_calc.calculation_shown"
    number: int
    level: int
