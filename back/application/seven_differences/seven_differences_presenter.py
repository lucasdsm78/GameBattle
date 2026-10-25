from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.seven_differences.models.seven_differences_state import (
    DIFFERENCE_COUNT,
    SevenDifferencesState,
)


class SevenDifferencesPresenter(GamePresenter[SevenDifferencesState]):
    def extras(self, state: SevenDifferencesState, teams: list[str]) -> dict[str, Any]:
        return {"differences_remaining": DIFFERENCE_COUNT - len(state.found_difference_ids)}

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        view = {**controller_view, "differences": []}
        if controller_view.get("phase") in {"idle", "memorizing"}:
            view["modified_image_url"] = ""
        return view
