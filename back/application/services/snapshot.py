from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import StrEnum
from itertools import count
from typing import Any

from domain.events import DomainEvent
from domain.models.game_config import GameConfig

_revisions = count(1)


class ClientRole(StrEnum):
    CONTROLLER = "controller"
    DISPLAY = "display"


@dataclass(frozen=True, slots=True)
class GameConfigSnapshot:
    """Vues prêtes à diffuser d'un état de partie.

    Créé uniquement sous le verrou de mutation : `revision` croît donc avec l'état, ce qui permet
    aux clients temps réel d'ignorer un instantané plus ancien que celui déjà reçu.
    """

    revision: int
    controller: dict[str, Any]
    display: dict[str, Any]
    events: tuple[dict[str, Any], ...] = ()

    @classmethod
    def from_domain(cls, config: GameConfig, events: Iterable[DomainEvent] = ()) -> GameConfigSnapshot:
        controller, display = config.client_views()
        return cls(revision=next(_revisions), controller=controller, display=display, events=tuple(map(serialize_event, events)))

    def for_role(self, role: ClientRole) -> dict[str, Any]:
        return self.display if role is ClientRole.DISPLAY else self.controller


def serialize_event(event: DomainEvent) -> dict[str, Any]:
    return {"type": event.name, **asdict(event)}
