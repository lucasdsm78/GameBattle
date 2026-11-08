from __future__ import annotations

from infrastructure.database.games.auction.auction_game_model import AuctionGameModel
from infrastructure.database.games.auction.auction_mapper import AuctionMapper
from infrastructure.database.games.shared.game_state_repository import (
    GameStateRepository,
)


class AuctionRepository(GameStateRepository):
    model = AuctionGameModel
    mapper = AuctionMapper()
