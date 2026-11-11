from __future__ import annotations

from typing import Any

from application.memory.memory_rules import MEMORY_RULES
from application.shared.constants.answer_masks import HIDDEN_ANSWER
from application.shared.game_presenter import GamePresenter
from domain.memory.constants.memory_limits import MEMORY_CHAIN_LENGTH
from domain.memory.models.memory_state import MemoryState


class MemoryPresenter(GamePresenter[MemoryState]):
    rules = MEMORY_RULES

    def extras(self, state: MemoryState, teams: list[str]) -> dict[str, Any]:
        return {"sequence_length": len(state.validated_answers), "chain_length": MEMORY_CHAIN_LENGTH}

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        view = {**controller_view, "validated_answers": []}
        question = controller_view.get("current_question")
        if isinstance(question, dict):
            view["current_question"] = {**question, "answer": HIDDEN_ANSWER, "explanation": ""}
        return view
