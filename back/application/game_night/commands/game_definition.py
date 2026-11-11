from __future__ import annotations

from pydantic import Field

from application.game_night.commands.fields import GameKey
from application.shared.commands.input_model import InputModel


class GameDefinitionModel(InputModel):
    game_key: GameKey
    label: str = Field(min_length=2, max_length=50)
    enabled: bool = True
    round_count: int = Field(ge=0, le=20)
