from __future__ import annotations

from infrastructure.database.games.golden_family.golden_family_game_model import (
    GoldenFamilyGameModel,
)
from infrastructure.database.games.golden_family.golden_family_mapper import (
    GoldenFamilyMapper,
)
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class GoldenFamilyRepository(GameStateRepository):
    model = GoldenFamilyGameModel
    mapper = GoldenFamilyMapper()
