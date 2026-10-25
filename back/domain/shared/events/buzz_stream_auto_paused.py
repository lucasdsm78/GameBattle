from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from domain.shared.events.domain_event import DomainEvent


@dataclass(frozen=True, slots=True)
class BuzzStreamAutoPaused(DomainEvent):
    """Personne n'a buzzé depuis longtemps : le défilement s'est mis en pause tout seul."""

    name: ClassVar[str] = "buzz_stream.auto_paused"
    game_key: str
    unanswered_items: int
