from __future__ import annotations

from infrastructure.database.games.blindtest.blindtest_game_model import (
    BlindtestGameModel,
)
from infrastructure.database.games.blindtest.blindtest_mapper import BlindtestMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class BlindtestRepository(GameStateRepository):
    model = BlindtestGameModel
    mapper = BlindtestMapper()
