from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Optional

from application.game_config.game_config_command_usecase import (
    GameConfigCommandUseCase,
    GameConfigCommandUseCaseImpl,
)
from application.game_config.game_config_query_usecase import GameConfigQueryUseCase, GameConfigQueryUseCaseImpl
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.config import Settings
from infrastructure.postgresql.database import configure_database
from infrastructure.postgresql.game_config.postgresql_game_config_repository import PostgreSQLGameConfigRepository
from infrastructure.realtime.websocket_hub import WebSocketHub
from infrastructure.spotify.spotify_playlist_service import SpotifyPlaylistService


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    configure_database(settings)
    return settings


@lru_cache()
def game_config_repository_singleton() -> GameConfigRepository:
    get_settings()
    return PostgreSQLGameConfigRepository()


@lru_cache()
def websocket_hub_singleton() -> WebSocketHub:
    return WebSocketHub()


@lru_cache()
def spotify_playlist_service_singleton() -> SpotifyPlaylistService:
    settings = get_settings()
    return SpotifyPlaylistService(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )


def game_config_command_usecase() -> GameConfigCommandUseCase:
    return GameConfigCommandUseCaseImpl(game_config_repository_singleton(), spotify_playlist_service_singleton())


def game_config_query_usecase() -> GameConfigQueryUseCase:
    return GameConfigQueryUseCaseImpl(game_config_repository_singleton())


def authorize_client(client_type: str, token: Optional[str]) -> bool:
    settings = get_settings()
    if client_type == "controller":
        return bool(token) and secrets.compare_digest(token, settings.controller_token)
    if client_type == "display":
        return bool(token) and secrets.compare_digest(token, settings.display_token)
    return False


def authorize_hardware_token(token: Optional[str]) -> bool:
    settings = get_settings()
    return bool(token) and secrets.compare_digest(token, settings.hardware_token)


