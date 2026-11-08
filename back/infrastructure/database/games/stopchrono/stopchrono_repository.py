from __future__ import annotations

from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)
from infrastructure.database.games.stopchrono.stopchrono_game_model import (
    StopchronoGameModel,
)
from infrastructure.database.games.stopchrono.stopchrono_mapper import StopchronoMapper


class StopchronoRepository(GameStateRepository):
    model = StopchronoGameModel
    mapper = StopchronoMapper()
