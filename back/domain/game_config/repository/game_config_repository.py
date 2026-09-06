from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from domain.game_config.model.game_config import GameConfig


class GameConfigRepository(ABC):
    @property
    def mutation_lock(self) -> asyncio.Lock:
        """Verrou commun aux use cases partageant cette instance de repository."""
        current_loop = asyncio.get_running_loop()
        lock = getattr(self, "_mutation_lock", None)
        lock_loop = getattr(self, "_mutation_lock_loop", None)
        if lock is None or lock_loop is not current_loop:
            lock = asyncio.Lock()
            self._mutation_lock = lock
            self._mutation_lock_loop = current_loop
        return lock

    @abstractmethod
    async def get_current(self) -> GameConfig:
        raise NotImplementedError

    @abstractmethod
    async def save(self, game_config: GameConfig) -> GameConfig:
        raise NotImplementedError

