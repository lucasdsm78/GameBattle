from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.games.shared.game_state_columns import GameStateColumns


class FairPriceGameModel(GameStateColumns, Base):
    __tablename__ = "fair_price_games"
