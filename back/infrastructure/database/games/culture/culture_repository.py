from __future__ import annotations

from infrastructure.database.games.culture.culture_game_model import CultureGameModel
from infrastructure.database.games.culture.culture_mapper import CultureMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class CultureRepository(GameStateRepository):
    model = CultureGameModel
    mapper = CultureMapper()
