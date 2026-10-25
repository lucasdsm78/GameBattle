from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.vanishing_word.models.vanishing_word_state import (
    HIDDEN_PHASES,
    VANISHING_WORD_MEMORIZATION_MS,
    VANISHING_WORD_WINNING_SCORE,
    VanishingWordState,
)
from domain.vanishing_word.services.vanishing_word_catalog import WORDS_PER_LIST


class VanishingWordPresenter(GamePresenter[VanishingWordState]):
    internal_fields = frozenset({"used_words"})

    def extras(self, state: VanishingWordState, teams: list[str]) -> dict[str, Any]:
        return {
            "memorization_ms": VANISHING_WORD_MEMORIZATION_MS,
            "winning_score": VANISHING_WORD_WINNING_SCORE,
            "words_per_list": WORDS_PER_LIST,
        }

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        # Tant que le mot n'est pas révélé, l'écran ne reçoit ni la liste d'origine ni le mot disparu.
        if controller_view.get("phase") in HIDDEN_PHASES:
            return {**controller_view, "words": [], "vanished_word": ""}
        return controller_view
