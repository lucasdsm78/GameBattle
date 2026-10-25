from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.flash_calc.models.flash_calc_state import (
    FLASH_CALC_FEEDBACK_MS,
    FLASH_CALC_WINNING_SCORE,
    FlashCalcState,
)
from domain.flash_calc.services.flash_calc_generator import (
    CALCS_PER_LEVEL,
    MAX_LEVEL,
    display_ms_for,
)


class FlashCalcPresenter(GamePresenter[FlashCalcState]):
    # Personne, régie comprise, ne doit savoir si le calcul affiché est juste avant un buzz.
    internal_fields = frozenset({"true_result"})

    def extras(self, state: FlashCalcState, teams: list[str]) -> dict[str, Any]:
        return {
            "level": state.level,
            "max_level": MAX_LEVEL,
            "calcs_per_level": CALCS_PER_LEVEL,
            "calc_duration_ms": display_ms_for(state.level),
            "feedback_ms": FLASH_CALC_FEEDBACK_MS,
            "winning_score": FLASH_CALC_WINNING_SCORE,
        }
