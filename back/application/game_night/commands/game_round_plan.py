from __future__ import annotations

from pydantic import Field

from application.game_night.commands.fields import GameKey
from application.shared.commands.input_model import InputModel


class GameRoundPlanModel(InputModel):
    id: str = Field(min_length=3, max_length=50)
    label: str = Field(min_length=2, max_length=50)
    game_key: GameKey
    planned_track_count: int = Field(ge=1, le=100)
    buzzer_enabled: bool = False
