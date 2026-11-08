from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.games.shared.game_state_columns import GameStateColumns


class GoldenFamilyGameModel(GameStateColumns, Base):
    __tablename__ = "golden_family_games"
