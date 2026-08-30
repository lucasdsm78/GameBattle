from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GAMEBATTLE_",
        case_sensitive=False,
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "GameBattle API"
    environment: str = Field(default="development", min_length=2, max_length=30)
    allowed_origins: str = "http://localhost:5173,http://localhost:8081"
    controller_token: str = Field(default="change-me-controller", min_length=8)
    display_token: str = Field(default="change-me-display", min_length=8)
    hardware_token: str = Field(default="change-me-hardware", min_length=8)
    database_url: str = Field(default="postgresql+asyncpg://gamebattle:gamebattle@localhost:5432/gamebattle", min_length=1)
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    blindtest_playlist_url: str = ""
    docs_enabled: bool = True

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def fastapi_docs_urls(self) -> dict[str, Optional[str]]:
        if self.docs_enabled:
            return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}

    @property
    def is_production(self) -> bool:
        return self.environment in {"prod", "production"}

