from __future__ import annotations

import asyncio
import json
from pathlib import Path

from domain.game_config.model.game_config import GameConfig, build_default_game_config
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.game_config_payload_mapper import game_config_from_payload


class FileGameConfigRepository(GameConfigRepository):
    def __init__(self, state_file: Path) -> None:
        self.state_file = state_file
        self._lock = asyncio.Lock()

    async def get_current(self) -> GameConfig:
        async with self._lock:
            if not self.state_file.exists():
                default_config = build_default_game_config()
                await self._write(default_config)
                return default_config
            return self._read()

    async def save(self, game_config: GameConfig) -> GameConfig:
        async with self._lock:
            await self._write(game_config)
            return game_config

    def _read(self) -> GameConfig:
        payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        return game_config_from_payload(payload)

    async def _write(self, game_config: GameConfig) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(game_config.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

