from __future__ import annotations

from typing import Any

from application.shared.buzz_stream_presenter import BuzzStreamPresenter
from domain.right_flag.models.right_flag_state import RightFlagState
from domain.right_flag.services.flag_catalog import FLAGS_PER_ROUND


class RightFlagPresenter(BuzzStreamPresenter[RightFlagState]):
    # La série à venir ne quitte jamais le serveur : sinon on connaîtrait la position du bon drapeau.
    internal_fields = frozenset({"flags", "used_countries"})

    def extras(self, state: RightFlagState, teams: list[str]) -> dict[str, Any]:
        return {
            **super().extras(state, teams),
            "answer_revealed": state.answer_revealed,
            "flag_number": state.flag_index + 1 if state.flags else 0,
            "flags_per_round": FLAGS_PER_ROUND,
        }

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        # La régie voit le bon drapeau ; l'écran public seulement une fois qu'il est trouvé ou révélé.
        if controller_view.get("answer_revealed"):
            return controller_view
        return {**controller_view, "country_code": ""}
