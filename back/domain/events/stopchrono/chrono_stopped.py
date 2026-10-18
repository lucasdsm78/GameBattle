from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class ChronoStopped(DomainEvent):
    name: ClassVar[str] = "stopchrono.stopped"
    team: str
    elapsed_ms: int
    delta_ms: int
