from __future__ import annotations

from infrastructure.database.games.flash_calc.flash_calc_game_model import (
    FlashCalcGameModel,
)
from infrastructure.database.games.flash_calc.flash_calc_mapper import FlashCalcMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class FlashCalcRepository(GameStateRepository):
    model = FlashCalcGameModel
    mapper = FlashCalcMapper()
