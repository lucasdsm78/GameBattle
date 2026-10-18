from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class BuzzerPressed(DomainEvent):
    name: ClassVar[str] = "buzzer.pressed"
    game_key: str
    team: str
