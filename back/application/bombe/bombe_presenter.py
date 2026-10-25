from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.bombe.models.bombe_state import BombeState


class BombePresenter(GamePresenter[BombeState]):
    def controller_view(self, state: BombeState, teams: list[str]) -> dict[str, Any]:
        view = super().controller_view(state, teams)
        # Le résultat du dé reste secret pour tous, régie comprise, tant qu'il roule.
        return {**view, "die_result": ""} if state.phase == "rolling" else view
