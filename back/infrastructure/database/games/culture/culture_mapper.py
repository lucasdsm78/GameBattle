from __future__ import annotations

from domain.culture.models.culture_state import CultureState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class CultureMapper(GameStateMapper[CultureState]):
    state_type = CultureState
    schema_version = 1
