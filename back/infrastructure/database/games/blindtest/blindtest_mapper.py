from __future__ import annotations

from domain.blindtest.models.blindtest_state import BlindtestState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class BlindtestMapper(GameStateMapper[BlindtestState]):
    state_type = BlindtestState
    schema_version = 1
