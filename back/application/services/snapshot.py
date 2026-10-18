from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import count
from typing import Any

from domain.models.game_config import GameConfig

_revisions = count(1)


class ClientRole(StrEnum):
    CONTROLLER = "controller"
    DISPLAY = "display"
    HARDWARE = "hardware"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class GameConfigSnapshot:
    """Vues prêtes à diffuser d'un état de partie.

    Créé uniquement sous le verrou de mutation : `revision` croît donc avec l'état, ce qui permet
    aux clients temps réel d'ignorer un instantané plus ancien que celui déjà reçu.
    """

    revision: int
    controller: dict[str, Any]
    display: dict[str, Any]

    @classmethod
    def from_domain(cls, config: GameConfig) -> GameConfigSnapshot:
        controller, display = config.client_views()
        return cls(revision=next(_revisions), controller=controller, display=display)

    def for_role(self, role: ClientRole) -> dict[str, Any]:
        return self.display if role is ClientRole.DISPLAY else self.controller
