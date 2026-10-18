from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, StringConstraints, field_validator

from application.shared.commands import CultureDifficulty, InputModel, TeamName
from domain.models.game_config import GameConfig
from domain.models.settings import GameDefinition, GameRoundPlan, GameSettings

GameKey = Literal["blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word"]
GameStatus = Literal["configuring", "ready", "live", "finished"]


class GameSettingsModel(InputModel):
    game_title: str = Field(min_length=3, max_length=60)
    random_round_order: bool = True
    teams: list[TeamName] = Field(min_length=2, max_length=6)
    buzzer_keys: list[Annotated[str, StringConstraints(max_length=20)]] = Field(default_factory=list, max_length=6)
    total_rounds: int = Field(default=1, ge=1, le=30)
    culture_difficulty: CultureDifficulty = "toutes"


class GameDefinitionModel(InputModel):
    game_key: GameKey
    label: str = Field(min_length=2, max_length=50)
    enabled: bool = True
    round_count: int = Field(ge=0, le=20)


class GameRoundPlanModel(InputModel):
    id: str = Field(min_length=3, max_length=50)
    label: str = Field(min_length=2, max_length=50)
    game_key: GameKey
    planned_track_count: int = Field(ge=1, le=100)
    buzzer_enabled: bool = False


class GameConfigUpsertModel(InputModel):
    settings: GameSettingsModel
    games: list[GameDefinitionModel] = Field(min_length=1, max_length=10)
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
