from __future__ import annotations

from typing import Any

from application.blindtest.blindtest_rules import BLINDTEST_RULES
from application.shared.game_presenter import GamePresenter
from domain.blindtest.models.blindtest_state import BlindtestState


class BlindtestPresenter(GamePresenter[BlindtestState]):
    rules = BLINDTEST_RULES

    def extras(self, state: BlindtestState, teams: list[str]) -> dict[str, Any]:
        return {"tracks_remaining": state.tracks_remaining}

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        view = {**controller_view, "tracks": []}
        current_track = controller_view.get("current_track")
        if not controller_view.get("revealed") and isinstance(current_track, dict):
            view["current_track"] = {
                **current_track,
                "title": "Titre masqué",
                "artist": "Artiste masqué",
                "preview_url": "",
                "artwork_url": "",
            }
        return view
