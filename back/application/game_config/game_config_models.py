from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from domain.game_config.model.game_config import (
    GameConfig,
    GameDefinition,
    GameRoundPlan,
    GameSettings,
)


class GameSettingsModel(BaseModel):
    game_title: str = Field(min_length=3, max_length=60)
    random_round_order: bool = True
    teams: list[str] = Field(min_length=2, max_length=6)
    buzzer_keys: list[str] = Field(default_factory=list, max_length=6)
    total_rounds: int = Field(default=1, ge=1, le=30)
    culture_difficulty: Literal["toutes", "facile", "moyen", "difficile"] = "toutes"


class GameDefinitionModel(BaseModel):
    game_key: Literal["blindtest", "stopchrono", "culture"]
    label: str = Field(min_length=2, max_length=50)
    enabled: bool = True
    round_count: int = Field(ge=0, le=20)


class GameRoundPlanModel(BaseModel):
    id: str = Field(min_length=3, max_length=50)
    label: str = Field(min_length=2, max_length=50)
    game_key: Literal["blindtest", "stopchrono", "culture"]
    planned_track_count: int = Field(ge=1, le=100)
    buzzer_enabled: bool = False


class GameConfigUpsertModel(BaseModel):
    settings: GameSettingsModel
    games: list[GameDefinitionModel] = Field(min_length=1, max_length=10)
    rounds: list[GameRoundPlanModel] = Field(default_factory=list, max_length=30)
    status: str = Field(default="configuring", max_length=30)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"configuring", "ready", "live", "finished"}:
            raise ValueError("Le statut doit être configuring, ready, live ou finished.")
        return normalized

    def to_domain(self) -> GameConfig:
        return GameConfig(
            settings=GameSettings(**self.settings.model_dump()),
            games=[GameDefinition(**game_payload.model_dump()) for game_payload in self.games],
            rounds=[GameRoundPlan(**round_payload.model_dump()) for round_payload in self.rounds],
            status=self.status,
        )


class GameConfigReadModel(BaseModel):
    settings: GameSettingsModel
    games: list[GameDefinitionModel]
    rounds: list[GameRoundPlanModel]
    session: dict[str, Any]
    status: str
    updated_at: str
    summary: dict[str, Any]

    @classmethod
    def from_domain(cls, game_config: GameConfig) -> "GameConfigReadModel":
        payload = game_config.to_dict()
        session = payload.get("session")
        if isinstance(session, dict):
            # La séquence complète des prochains jeux reste persistée dans l'agrégat, mais ne doit
            # jamais être exposée aux clients (mobile, écran, API HTTP) pour préserver la surprise.
            session.pop("round_sequence", None)
        return cls(**payload)


class BlindtestAnswerCommandModel(BaseModel):
    is_correct: bool


class BlindtestBuzzerCommandModel(BaseModel):
    team: str = Field(min_length=2, max_length=40)


class BlindtestPlaylistSeedTrackModel(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    artist: str = Field(min_length=1, max_length=120)
    preview_url: str = Field(default="", max_length=500)
    artwork_url: str = Field(default="", max_length=500)


class BlindtestPlaylistCommandModel(BaseModel):
    tracks: list[BlindtestPlaylistSeedTrackModel] = Field(min_length=1, max_length=100)


class BlindtestPlaybackCommandModel(BaseModel):
    action: Literal["play", "pause", "resume", "stop", "seek"]
    position_ms: int | None = Field(default=None, ge=0)


class BlindtestPlaybackSyncCommandModel(BaseModel):
    track_id: str = Field(default="", max_length=120)
    playback_state: Literal["stopped", "playing", "paused"]
    position_ms: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)


class CultureDifficultyCommandModel(BaseModel):
    difficulty: Literal["toutes", "facile", "moyen", "difficile"]


class SpotifyPlaylistImportCommandModel(BaseModel):
    playlist_url: str = Field(min_length=10, max_length=500)


class GameConfigEnvelope(BaseModel):
    type: str
    payload: GameConfigReadModel

