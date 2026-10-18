from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class BombeDieRolling(DomainEvent):
    name: ClassVar[str] = "bombe.die_rolling"
    team: str
