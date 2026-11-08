from __future__ import annotations

from domain.vanishing_word.models.vanishing_word_state import VanishingWordState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class VanishingWordMapper(GameStateMapper[VanishingWordState]):
    state_type = VanishingWordState
    schema_version = 1
