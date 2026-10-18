from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from domain.models.game_config import GameConfig
from domain.models.settings import GameDefinition, GameRoundPlan, GameSettings

GameKey = Literal["blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word"]
GameStatus = Literal["configuring", "ready", "live", "finished"]
CultureDifficulty = Literal["toutes", "facile", "moyen", "difficile"]

TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
Slug = Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"^[a-z0-9_-]+$")]
# Positions audio issues des lecteurs natifs : un flottant entier (ex. 12000.0) reste accepté.
DurationMs = Annotated[int, Field(ge=0, le=24 * 60 * 60 * 1000, strict=False)]


class InputModel(BaseModel):
    """Entrée client : types stricts, champs inconnus refusés, espaces superflus retirés."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True, frozen=True)


# --- Configuration de partie ---


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


# --- Commandes de jeu ---


class TeamCommand(InputModel):
    team: TeamName


class AnswerCommand(InputModel):
    is_correct: bool


class PlaybackControlCommand(InputModel):
    action: Literal["play", "pause", "resume", "stop", "seek"]
    position_ms: DurationMs | None = None


class PlaybackSyncCommand(InputModel):
    track_id: str = Field(default="", max_length=120)
    playback_state: Literal["stopped", "playing", "paused"]
    position_ms: DurationMs = 0
    duration_ms: DurationMs = 0


class PlaylistSeedTrack(InputModel):
    title: str = Field(min_length=1, max_length=120)
    artist: str = Field(min_length=1, max_length=120)
    preview_url: str = Field(default="", max_length=500)
    artwork_url: str = Field(default="", max_length=500)


class PlaylistLoadCommand(InputModel):
    tracks: list[PlaylistSeedTrack] = Field(min_length=1, max_length=100)


class SpotifyPlaylistImportCommand(InputModel):
    playlist_url: str = Field(min_length=10, max_length=500)


class SpotifyTokenCommand(InputModel):
    access_token: str = Field(min_length=1, max_length=2048, pattern=r"^[A-Za-z0-9._~+/=-]+$")


class CultureDifficultyCommand(InputModel):
    difficulty: CultureDifficulty


class SevenDifferenceFoundCommand(InputModel):
    difference_id: Slug


class AuctionBidCommand(InputModel):
    team: TeamName
    target_count: int = Field(ge=1, le=100)


class ForbiddenWordCardCommand(InputModel):
    card_id: Slug
