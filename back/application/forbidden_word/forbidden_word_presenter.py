from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.forbidden_word.models.forbidden_word_state import ForbiddenWordState


class ForbiddenWordPresenter(GamePresenter[ForbiddenWordState]):
    internal_fields = frozenset({"used_card_ids"})

    def extras(self, state: ForbiddenWordState, teams: list[str]) -> dict[str, Any]:
        return {"current_team": state.current_team, "scores": state.scores(teams), "turn_duration_ms": state.turn_duration_ms}

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        # Le mot et ses mots interdits ne quittent jamais la régie : l'équipe qui devine regarde l'écran.
        return {**controller_view, "current_card": None}
