from __future__ import annotations

from domain.auction.models.auction_state import AuctionState
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class AuctionMapper(GameStateMapper[AuctionState]):
    state_type = AuctionState
    schema_version = 1
