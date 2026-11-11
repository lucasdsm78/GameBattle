from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class HostChanged(DomainEvent):
    """L'hôte est parti : le plus ancien membre prend la main."""

    name: ClassVar[str] = "room.host_changed"
    host: str
