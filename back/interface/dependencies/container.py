from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Optional

from application.accounts.account_maintenance import AccountMaintenance
from application.accounts.account_usecase import AccountUseCase
from application.blindtest.playlist_service import BlindtestPlaylistService
from application.game_night.game_night_query_usecase import GameNightQueryUseCase
from application.rooms.room_command_usecase import RoomCommandUseCase
from application.rooms.room_query_usecase import RoomQueryUseCase
from application.use_cases import GameUseCases
from infrastructure.config import Settings
from infrastructure.database.database import Database
from infrastructure.database.outbox.outbox_store import OutboxStore
from infrastructure.database.single_instance_lock import SingleInstanceLock
from infrastructure.extern.spotify import SpotifyPlaylistService
from infrastructure.repositories.accounts.account_unit_of_work import (
    SqlAccountUnitOfWork,
)
from infrastructure.repositories.game_night.cached_game_config import (
    CachedGameConfigRepository,
)
from infrastructure.repositories.game_night.game_config_unit_of_work import (
    GameConfigUnitOfWork,
)
from infrastructure.repositories.game_night.postgresql_game_config import (
    PostgreSQLGameConfigRepository,
)
from infrastructure.repositories.rooms.room_unit_of_work import SqlRoomUnitOfWork
from infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from interface.realtime.deadline_worker import GameDeadlineWorker
from interface.realtime.dispatcher import RealtimeDispatcher
from interface.realtime.hub import WebSocketHub
from interface.realtime.room_broadcaster import RoomBroadcaster
from interface.realtime.room_hub import RoomHub
from interface.realtime.routes import ROUTES
from interface.workers.account_janitor import AccountJanitor
from interface.workers.outbox_relay import OutboxRelay
from interface.workers.relay_notifier import RelayNotifier
from interface.workers.room_janitor import RoomJanitor


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def database() -> Database:
    return Database(get_settings().database_url)


@lru_cache
def single_instance_lock() -> SingleInstanceLock:
    return SingleInstanceLock(database())


@lru_cache
def game_config_repository() -> CachedGameConfigRepository:
    return CachedGameConfigRepository(PostgreSQLGameConfigRepository(database()))


@lru_cache
def unit_of_work() -> GameConfigUnitOfWork:
    return GameConfigUnitOfWork(game_config_repository())


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
def game_use_cases() -> GameUseCases:
    return GameUseCases.build(unit_of_work(), websocket_hub(), blindtest_playlist_service())


@lru_cache
def realtime_dispatcher() -> RealtimeDispatcher:
    return RealtimeDispatcher(game_use_cases(), ROUTES)


@lru_cache
def game_night_query_usecase() -> GameNightQueryUseCase:
    return GameNightQueryUseCase(unit_of_work())


def account_unit_of_work() -> SqlAccountUnitOfWork:
    return SqlAccountUnitOfWork(database(), get_settings().rate_limit_secret.encode("utf-8"))


@lru_cache
def account_usecase() -> AccountUseCase:
    return AccountUseCase(account_unit_of_work, Argon2PasswordHasher())


def room_unit_of_work() -> SqlRoomUnitOfWork:
    return SqlRoomUnitOfWork(database(), get_settings().rate_limit_secret.encode("utf-8"))


@lru_cache
def room_command_usecase() -> RoomCommandUseCase:
    return RoomCommandUseCase(room_unit_of_work, notifier=RelayNotifier(outbox_relay))


@lru_cache
def room_query_usecase() -> RoomQueryUseCase:
    return RoomQueryUseCase(room_unit_of_work)


@lru_cache
def room_hub() -> RoomHub:
    return RoomHub()


@lru_cache
def room_broadcaster() -> RoomBroadcaster:
    return RoomBroadcaster(room_query_usecase(), room_hub())


@lru_cache
def outbox_store() -> OutboxStore:
    return OutboxStore(database())


@lru_cache
def outbox_relay() -> OutboxRelay:
    return OutboxRelay(outbox_store(), room_broadcaster())


def room_janitor() -> RoomJanitor:
    return RoomJanitor(room_command_usecase(), outbox_store())


def account_janitor() -> AccountJanitor:
    return AccountJanitor(AccountMaintenance(account_unit_of_work))


def game_deadline_worker() -> GameDeadlineWorker:
    return GameDeadlineWorker(game_use_cases().game_night)


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
        single_instance_lock,
        game_config_repository,
        unit_of_work,
        websocket_hub,
        spotify_playlist_service,
        blindtest_playlist_service,
        game_use_cases,
        realtime_dispatcher,
        game_night_query_usecase,
        account_usecase,
        room_command_usecase,
        room_query_usecase,
        room_hub,
        room_broadcaster,
        outbox_store,
        outbox_relay,
    ):
        factory.cache_clear()
