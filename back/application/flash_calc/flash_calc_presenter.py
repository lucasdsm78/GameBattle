from __future__ import annotations

from typing import Any

from application.shared.buzz_stream_presenter import BuzzStreamPresenter
from domain.flash_calc.models.flash_calc_state import FlashCalcState
from domain.flash_calc.services.flash_calc_generator import (
    CALCS_PER_LEVEL,
    MAX_LEVEL,
    display_ms_for,
)


class FlashCalcPresenter(BuzzStreamPresenter[FlashCalcState]):
    # Personne, régie comprise, ne doit savoir si le calcul affiché est juste avant un buzz.
    internal_fields = frozenset({"true_result"})

    def extras(self, state: FlashCalcState, teams: list[str]) -> dict[str, Any]:
        return {
            **super().extras(state, teams),
            "level": state.level,
            "max_level": MAX_LEVEL,
            "calcs_per_level": CALCS_PER_LEVEL,
            "calc_duration_ms": display_ms_for(state.level),
        }
