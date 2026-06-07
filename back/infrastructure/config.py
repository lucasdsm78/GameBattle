from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
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
    environment: str = "development"
    allowed_origins: str = "http://localhost:5173,http://localhost:8081"
    controller_token: str = "change-me-controller"
    display_token: str = "change-me-display"
    hardware_token: str = "change-me-hardware"
    database_url: str = "postgresql+asyncpg://gamebattle:gamebattle@localhost:5432/gamebattle"
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    docs_enabled: bool = True

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def fastapi_docs_urls(self) -> dict[str, Optional[str]]:
        if self.docs_enabled:
            return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}

