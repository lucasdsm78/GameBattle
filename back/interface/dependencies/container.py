from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Optional

from application.commands import ALL_COMMANDS
from application.commands.bus import GameCommandBus
from application.queries.game_config import GameConfigQueryService
from application.services.playlist import BlindtestPlaylistService
from infrastructure.config import Settings
from infrastructure.database.database import Database
from infrastructure.extern.spotify import SpotifyPlaylistService
from infrastructure.repositories.cached_game_config import CachedGameConfigRepository
from infrastructure.repositories.postgresql_game_config import (
    PostgreSQLGameConfigRepository,
)
from interface.realtime.deadline_worker import GameDeadlineWorker
from interface.realtime.hub import WebSocketHub


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def database() -> Database:
    return Database(get_settings().database_url)


@lru_cache
def game_config_repository() -> CachedGameConfigRepository:
    return CachedGameConfigRepository(PostgreSQLGameConfigRepository(database()))


@lru_cache
def websocket_hub() -> WebSocketHub:
    return WebSocketHub()


@lru_cache
def spotify_playlist_service() -> SpotifyPlaylistService:
    return SpotifyPlaylistService()


@lru_cache
def blindtest_playlist_service() -> BlindtestPlaylistService:
    return BlindtestPlaylistService(spotify_playlist_service(), get_settings().blindtest_playlist_url)


@lru_cache
def game_command_bus() -> GameCommandBus:
    return GameCommandBus(game_config_repository(), blindtest_playlist_service(), websocket_hub(), ALL_COMMANDS)


@lru_cache
def game_config_query_service() -> GameConfigQueryService:
    return GameConfigQueryService(game_config_repository())


def game_deadline_worker() -> GameDeadlineWorker:
    return GameDeadlineWorker(game_command_bus())


def authorize_client(client_type: str, token: Optional[str]) -> bool:
    settings = get_settings()
    expected = {"controller": settings.controller_token, "display": settings.display_token}.get(client_type)
    return expected is not None and _constant_time_equals(token, expected)


def authorize_hardware_token(token: Optional[str]) -> bool:
    return _constant_time_equals(token, get_settings().hardware_token)


def _constant_time_equals(candidate: Optional[str], expected: str) -> bool:
    return bool(candidate) and secrets.compare_digest(candidate.encode(), expected.encode())


def reset_dependency_caches() -> None:
    """Réinitialise les singletons (tests ou changement d'environnement)."""
    for factory in (
        get_settings,
        database,
        game_config_repository,
        websocket_hub,
        spotify_playlist_service,
        blindtest_playlist_service,
        game_command_bus,
        game_config_query_service,
    ):
        factory.cache_clear()
