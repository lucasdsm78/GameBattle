from __future__ import annotations

from infrastructure.database.games.seven_differences.seven_differences_game_model import (
    SevenDifferencesGameModel,
)
from infrastructure.database.games.seven_differences.seven_differences_mapper import (
    SevenDifferencesMapper,
)
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class SevenDifferencesRepository(GameStateRepository):
    model = SevenDifferencesGameModel
    mapper = SevenDifferencesMapper()
