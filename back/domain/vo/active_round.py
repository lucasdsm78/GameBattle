from __future__ import annotations

from dataclasses import dataclass

from domain.models.settings import SUPPORTED_GAME_KEYS
from exceptions import InvalidGameConfigError


@dataclass(slots=True)
class ActiveRound:
    round_id: str
    label: str
    game_key: str
    order_index: int
    completed: bool = False

    def validate(self) -> None:
        if self.game_key not in SUPPORTED_GAME_KEYS:
            raise InvalidGameConfigError(f"Jeu actif non supporté: {self.game_key}.")
        if self.order_index < 0:
            raise InvalidGameConfigError("L'ordre de la manche active est invalide.")
