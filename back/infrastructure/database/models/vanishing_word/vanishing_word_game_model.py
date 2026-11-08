from __future__ import annotations

from infrastructure.database.database import Base
from infrastructure.database.models.shared.game_state_columns import GameStateColumns


class VanishingWordGameModel(GameStateColumns, Base):
    __tablename__ = "vanishing_word_games"
