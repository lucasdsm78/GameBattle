from __future__ import annotations

from infrastructure.database.games.right_flag.right_flag_game_model import (
    RightFlagGameModel,
)
from infrastructure.database.games.right_flag.right_flag_mapper import RightFlagMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class RightFlagRepository(GameStateRepository):
    model = RightFlagGameModel
    mapper = RightFlagMapper()
