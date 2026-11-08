from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.games.shared.game_state_columns import GameStateColumns


class RightFlagGameModel(GameStateColumns, Base):
    __tablename__ = "right_flag_games"
