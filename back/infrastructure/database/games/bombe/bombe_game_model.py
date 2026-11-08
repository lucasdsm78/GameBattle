from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.games.shared.game_state_columns import GameStateColumns


class BombeGameModel(GameStateColumns, Base):
    __tablename__ = "bombe_games"
