from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from application.shared.commands.fields import CultureDifficulty, TeamName
from application.shared.commands.input_model import InputModel


class GameSettingsModel(InputModel):
    game_title: str = Field(min_length=3, max_length=60)
    random_round_order: bool = True
    teams: list[TeamName] = Field(min_length=2, max_length=6)
    buzzer_keys: list[Annotated[str, StringConstraints(max_length=20)]] = Field(default_factory=list, max_length=6)
    total_rounds: int = Field(default=1, ge=1, le=30)
    culture_difficulty: CultureDifficulty = "toutes"
