from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class BombeExploded(DomainEvent):
    name: ClassVar[str] = "bombe.exploded"
    team: str
