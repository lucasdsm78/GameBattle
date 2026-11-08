from __future__ import annotations

from infrastructure.database.games.fair_price.fair_price_game_model import (
    FairPriceGameModel,
)
from infrastructure.database.games.fair_price.fair_price_mapper import FairPriceMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class FairPriceRepository(GameStateRepository):
    model = FairPriceGameModel
    mapper = FairPriceMapper()
