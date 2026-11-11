from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from application.game_night.commands.fields import GameStatus
from application.game_night.commands.game_definition import GameDefinitionModel
from application.game_night.commands.game_round_plan import GameRoundPlanModel
from application.game_night.commands.game_settings import GameSettingsModel
from application.shared.commands.input_model import InputModel
from domain.game_night.constants.game_night_limits import SUPPORTED_GAME_KEYS
from domain.game_night.models.game_config import GameConfig
from domain.game_night.models.settings import GameDefinition, GameRoundPlan, GameSettings


class GameConfigUpsertModel(InputModel):
    settings: GameSettingsModel
    games: list[GameDefinitionModel] = Field(min_length=1, max_length=len(SUPPORTED_GAME_KEYS))
    rounds: list[GameRoundPlanModel] = Field(default_factory=list, max_length=30)
    status: GameStatus = "configuring"

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    def to_domain(self) -> GameConfig:
        return GameConfig(
            settings=GameSettings(**self.settings.model_dump()),
            games=[GameDefinition(**game.model_dump()) for game in self.games],
            rounds=[GameRoundPlan(**round_plan.model_dump()) for round_plan in self.rounds],
            status=self.status,
        )
