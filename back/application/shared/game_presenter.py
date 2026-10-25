from __future__ import annotations

from dataclasses import asdict
from typing import Any, ClassVar

from domain.shared.models.game_state import GameState

HIDDEN_ANSWER = "Réponse masquée"


class GamePresenter[StateT: GameState]:
    """Vues client d'un jeu : la régie ne reçoit pas les données internes, l'écran public aucun secret.

    Ce que chaque client a le droit de voir est une règle de diffusion, pas une règle métier :
    elle vit ici, hors du domaine.
    """

    internal_fields: ClassVar[frozenset[str]] = frozenset()

    def extras(self, state: StateT, teams: list[str]) -> dict[str, Any]:
        """Valeurs calculées utiles aux apps (restants, constantes de règle…)."""
        return {}

    def controller_view(self, state: StateT, teams: list[str]) -> dict[str, Any]:
        view = {key: value for key, value in asdict(state).items() if key not in self.internal_fields}
        return {**view, **self.extras(state, teams)}

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        """Vue de l'écran public, dérivée de celle de la régie. Ne mute jamais `controller_view`."""
        return controller_view
