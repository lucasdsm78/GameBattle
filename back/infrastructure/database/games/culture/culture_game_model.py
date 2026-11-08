from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.games.shared.game_state_columns import GameStateColumns


class CultureGameModel(GameStateColumns, Base):
    __tablename__ = "culture_games"
