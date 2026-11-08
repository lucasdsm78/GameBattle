from __future__ import annotations

from domain.golden_family.models.golden_family_state import GoldenFamilyState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class GoldenFamilyMapper(GameStateMapper[GoldenFamilyState]):
    state_type = GoldenFamilyState
    schema_version = 1
