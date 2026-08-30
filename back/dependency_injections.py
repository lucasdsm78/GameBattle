from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Optional

from application.game_config.command import (
    GameConfigCommandUseCase,
    GameConfigCommandUseCaseImpl,
)
from application.game_config.game_config_query_usecase import GameConfigQueryUseCase, GameConfigQueryUseCaseImpl
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.config import Settings
from infrastructure.postgresql.game_config.postgresql_game_config_repository import PostgreSQLGameConfigRepository
from infrastructure.realtime.websocket_hub import WebSocketHub
from infrastructure.spotify.spotify_playlist_service import SpotifyPlaylistService


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def game_config_repository_singleton() -> GameConfigRepository:
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
    settings = get_settings()
    return GameConfigCommandUseCaseImpl(
        game_config_repository_singleton(),
        spotify_playlist_service_singleton(),
        default_playlist_url=settings.blindtest_playlist_url,
    )


def game_config_query_usecase() -> GameConfigQueryUseCase:
    return GameConfigQueryUseCaseImpl(game_config_repository_singleton())


def authorize_client(client_type: str, token: Optional[str]) -> bool:
    settings = get_settings()
    if client_type == "controller":
        return _constant_time_equals(token, settings.controller_token)
    if client_type == "display":
        return _constant_time_equals(token, settings.display_token)
    return False


def authorize_hardware_token(token: Optional[str]) -> bool:
    settings = get_settings()
    return _constant_time_equals(token, settings.hardware_token)


def _constant_time_equals(candidate: Optional[str], expected: str) -> bool:
    return bool(candidate) and secrets.compare_digest(candidate, expected)


def reset_dependency_caches() -> None:
    """Réinitialise les singletons applicatifs pour les tests ou les changements d'environnement."""
    get_settings.cache_clear()
    game_config_repository_singleton.cache_clear()
    websocket_hub_singleton.cache_clear()
    spotify_playlist_service_singleton.cache_clear()


