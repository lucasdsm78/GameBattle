from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self

from domain.shared.models.game_state import GameState


class GameActions:
    """Base des actions d'un jeu, portées par la racine d'agrégat de la soirée (mixin).

    Chaque jeu range ses actions dans `domain/<jeu>/models/<jeu>_actions.py` ; `GameConfig` les compose.
    Une action ne manipule jamais l'état du jeu directement : elle passe par `_play`, qui vérifie que ce
    jeu est la manche en cours, clôt la manche si un vainqueur est désigné et émet les événements.
    """

    __slots__ = ()

    # Fournis par la racine d'agrégat (déclarés ici pour documenter le contrat, sans dépendre de game_night/).
    session: Any

    @property
    def teams(self) -> list[str]:
        raise NotImplementedError

    def _play(self, game_key: str, transition: Callable[[Any], GameState]) -> Self:
        raise NotImplementedError

    def _replace_session(self, **session_changes: Any) -> Self:
        raise NotImplementedError
