from __future__ import annotations

from infrastructure.database.games.bombe.bombe_game_model import BombeGameModel
from infrastructure.database.games.bombe.bombe_mapper import BombeMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class BombeRepository(GameStateRepository):
    model = BombeGameModel
    mapper = BombeMapper()
