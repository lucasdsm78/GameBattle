from __future__ import annotations

from domain.right_flag.models.right_flag_state import RightFlagState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class RightFlagMapper(GameStateMapper[RightFlagState]):
    state_type = RightFlagState
    schema_version = 1
