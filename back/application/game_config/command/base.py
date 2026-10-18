from __future__ import annotations

from collections.abc import Awaitable, Callable
from inspect import isawaitable
import time

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.model.game_config import GameConfig
from domain.game_config.repository.game_config_repository import GameConfigRepository

ConfigTransform = Callable[[GameConfig], GameConfig | Awaitable[GameConfig]]


class GameConfigCommandBase:

    def __init__(self, repository: GameConfigRepository) -> None:
        self.repository = repository

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    async def _persist_unlocked(self, config: GameConfig) -> GameConfigReadModel:
        config.validate()
        persisted = await self.repository.save(config)
        return GameConfigReadModel.from_domain(persisted)

    async def _persist(self, config: GameConfig) -> GameConfigReadModel:
        async with self.repository.mutation_lock:
            return await self._persist_unlocked(config)

    async def _mutate(self, transform: ConfigTransform) -> GameConfigReadModel:
        async with self.repository.mutation_lock:
            result = transform(await self.repository.get_current())
            updated = await result if isawaitable(result) else result
            return await self._persist_unlocked(updated)

    async def _mutate_if_changed(self, transform: ConfigTransform) -> GameConfigReadModel | None:
        async with self.repository.mutation_lock:
            current = await self.repository.get_current()
            result = transform(current)
            updated = await result if isawaitable(result) else result
            if updated is current:
                return None
            return await self._persist_unlocked(updated)
