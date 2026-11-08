from __future__ import annotations

from domain.stopchrono.models.stopchrono_state import StopChronoState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class StopchronoMapper(GameStateMapper[StopChronoState]):
    state_type = StopChronoState
    schema_version = 1
