from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class FamilyControlTaken(DomainEvent):
    name: ClassVar[str] = "golden_family.control_taken"
    team: str
