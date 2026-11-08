from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.games.shared.game_state_columns import GameStateColumns


class SevenDifferencesGameModel(GameStateColumns, Base):
    __tablename__ = "seven_differences_games"
