from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.models.shared.game_state_columns import GameStateColumns


class BlindtestGameModel(GameStateColumns, Base):
    __tablename__ = "blindtest_games"
