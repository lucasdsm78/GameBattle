from __future__ import annotations

from infrastructure.database.games.forbidden_word.forbidden_word_game_model import (
    ForbiddenWordGameModel,
)
from infrastructure.database.games.forbidden_word.forbidden_word_mapper import (
    ForbiddenWordMapper,
)
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class ForbiddenWordRepository(GameStateRepository):
    model = ForbiddenWordGameModel
    mapper = ForbiddenWordMapper()
