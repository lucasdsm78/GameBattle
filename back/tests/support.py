from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from application.commands import GameUseCases
from application.services.snapshot import ClientRole, GameConfigSnapshot
from domain.models.game_config import GameConfig, build_default_game_config
from domain.repositories.game_config import GameConfigRepository
from interface.realtime.dispatcher import RealtimeDispatcher
from interface.realtime.routes import ROUTES


def started_config(game_key: str, *, teams: list[str] | None = None, total_rounds: int = 1) -> GameConfig:
    config = build_default_game_config()
    config.settings.teams = teams or ["Rouges", "Bleus", "Verts"]
    config.settings.buzzer_keys = [str(index + 1) for index in range(len(config.settings.teams))]
    config.settings.total_rounds = total_rounds
    for game in config.games:
        game.enabled = game.game_key == game_key
    return config.start_session()


class InMemoryRepository(GameConfigRepository):
    def __init__(self, config: GameConfig, *, delay_seconds: float = 0.0) -> None:
        self.current = config
        self.saves = 0
        self._delay_seconds = delay_seconds

    async def get_current(self) -> GameConfig:
        await asyncio.sleep(self._delay_seconds)
        return self.current

    async def save(self, game_config: GameConfig) -> GameConfig:
        await asyncio.sleep(self._delay_seconds)
        self.saves += 1
        self.current = game_config
        return game_config


class RecordingPublisher:
    def __init__(self) -> None:
        self.snapshots: list[GameConfigSnapshot] = []

    def publish(self, snapshot: GameConfigSnapshot) -> None:
        self.snapshots.append(snapshot)


class StubPlaylists:
    def __init__(self) -> None:
        self.user_token: str | None = None

    def set_user_token(self, token: str) -> None:
        self.user_token = token

    async def autoimport(self, config: GameConfig) -> GameConfig:
        return config


class GameHarness:
    """Use cases réels sur un dépôt en mémoire, pilotables directement ou via le protocole WebSocket."""

    def __init__(self, config: GameConfig, *, now_ms: int | Callable[[], int] = 1_000, delay_seconds: float = 0.0) -> None:
        self.repository = InMemoryRepository(config, delay_seconds=delay_seconds)
        self.publisher = RecordingPublisher()
        self.playlists = StubPlaylists()
        clock = now_ms if callable(now_ms) else (lambda: now_ms)
        self.use_cases = GameUseCases.build(self.repository, self.publisher, self.playlists, clock)  # type: ignore[arg-type]
        self.dispatcher = RealtimeDispatcher(self.use_cases, ROUTES)

    @property
    def config(self) -> GameConfig:
        return self.repository.current

    def run(self, name: str, payload: dict[str, Any] | None = None, role: ClientRole = ClientRole.CONTROLLER):
        return asyncio.run(self.dispatcher.dispatch(name, payload, role))
