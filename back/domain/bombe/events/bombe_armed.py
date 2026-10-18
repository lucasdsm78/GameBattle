from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class BombeArmed(DomainEvent):
    name: ClassVar[str] = "bombe.armed"
    team: str
    die_result: str
