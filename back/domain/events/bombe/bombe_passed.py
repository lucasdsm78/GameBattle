from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class BombePassed(DomainEvent):
    name: ClassVar[str] = "bombe.passed"
    from_team: str
    to_team: str
