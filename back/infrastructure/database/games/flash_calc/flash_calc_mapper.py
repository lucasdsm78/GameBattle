from __future__ import annotations

from domain.flash_calc.models.flash_calc_state import FlashCalcState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class FlashCalcMapper(GameStateMapper[FlashCalcState]):
    state_type = FlashCalcState
    schema_version = 1
