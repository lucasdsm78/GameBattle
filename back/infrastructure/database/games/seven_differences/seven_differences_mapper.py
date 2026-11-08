from __future__ import annotations

from domain.seven_differences.models.seven_differences_state import (
    SevenDifferencesState,
)
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class SevenDifferencesMapper(GameStateMapper[SevenDifferencesState]):
    state_type = SevenDifferencesState
    schema_version = 1
