from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from application.game_config.command_bus import GameCommandBus
from application.game_config.snapshot import ClientRole, GameConfigSnapshot
from application.games import ALL_COMMANDS
from domain.game_config.model.game_config import GameConfig, build_default_game_config
from domain.game_config.repository.game_config_repository import GameConfigRepository


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


class BusHarness:
    def __init__(self, config: GameConfig, *, now_ms: int | Callable[[], int] = 1_000, delay_seconds: float = 0.0) -> None:
        self.repository = InMemoryRepository(config, delay_seconds=delay_seconds)
        self.publisher = RecordingPublisher()
        self.playlists = StubPlaylists()
        clock = now_ms if callable(now_ms) else (lambda: now_ms)
        self.bus = GameCommandBus(self.repository, self.playlists, self.publisher, ALL_COMMANDS, clock=clock)  # type: ignore[arg-type]

    @property
    def config(self) -> GameConfig:
        return self.repository.current

    def run(self, name: str, payload: dict[str, Any] | None = None, role: ClientRole = ClientRole.CONTROLLER):
        return asyncio.run(self.bus.execute(name, payload, role))
