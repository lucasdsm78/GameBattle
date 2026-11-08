from __future__ import annotations

from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)
from infrastructure.database.games.vanishing_word.vanishing_word_game_model import (
    VanishingWordGameModel,
)
from infrastructure.database.games.vanishing_word.vanishing_word_mapper import (
    VanishingWordMapper,
)


class VanishingWordRepository(GameStateRepository):
    model = VanishingWordGameModel
    mapper = VanishingWordMapper()
