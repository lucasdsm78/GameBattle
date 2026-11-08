from __future__ import annotations

from infrastructure.database.games.memory.memory_game_model import MemoryGameModel
from infrastructure.database.games.memory.memory_mapper import MemoryMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class MemoryRepository(GameStateRepository):
    model = MemoryGameModel
    mapper = MemoryMapper()
