from __future__ import annotations

from typing import Any

from application.culture.culture_rules import CULTURE_RULES
from application.shared.constants.answer_masks import HIDDEN_ANSWER
from application.shared.game_presenter import GamePresenter
from domain.culture.models.culture_state import (
    CultureState,
)


class CulturePresenter(GamePresenter[CultureState]):
    rules = CULTURE_RULES

    def extras(self, state: CultureState, teams: list[str]) -> dict[str, Any]:
        return {"questions_remaining": state.questions_remaining}

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        question = controller_view.get("current_question")
        if not isinstance(question, dict):
            return controller_view
        hidden = {"explanation": ""} if controller_view.get("answered") else {"answer": HIDDEN_ANSWER, "explanation": ""}
        return {**controller_view, "current_question": {**question, **hidden}}
