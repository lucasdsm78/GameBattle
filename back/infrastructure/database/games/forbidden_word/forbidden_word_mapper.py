from __future__ import annotations

from domain.forbidden_word.models.forbidden_word_state import ForbiddenWordState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class ForbiddenWordMapper(GameStateMapper[ForbiddenWordState]):
    state_type = ForbiddenWordState
    schema_version = 1
