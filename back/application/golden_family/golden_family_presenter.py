from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.golden_family.models.golden_family_state import (
    GOLDEN_FAMILY_MAX_STRIKES,
    GOLDEN_FAMILY_WINNING_SCORE,
    GoldenFamilyState,
)

HIDDEN_FAMILY_ANSWER = {"text": "", "points": 0}


class GoldenFamilyPresenter(GamePresenter[GoldenFamilyState]):
    internal_fields = frozenset({"used_questions", "attempts"})

    def extras(self, state: GoldenFamilyState, teams: list[str]) -> dict[str, Any]:
        return {"winning_score": GOLDEN_FAMILY_WINNING_SCORE, "max_strikes": GOLDEN_FAMILY_MAX_STRIKES}

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        # L'écran public ne reçoit ni le texte ni les points d'une réponse avant qu'elle soit retournée.
        question = controller_view.get("question")
        if not isinstance(question, dict):
            return controller_view
        answers = [
            answer if slot["revealed"] else HIDDEN_FAMILY_ANSWER
            for answer, slot in zip(question["answers"], controller_view["board"])
        ]
        return {**controller_view, "question": {**question, "answers": answers}}
