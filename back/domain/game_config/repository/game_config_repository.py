from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from domain.game_config.model.game_config import GameConfig


class GameConfigRepository(ABC):
    @property
    def mutation_lock(self) -> asyncio.Lock:
        """Verrou commun aux use cases partageant cette instance de repository."""
        lock = getattr(self, "_mutation_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self._mutation_lock = lock
        return lock

    @abstractmethod
    async def get_current(self) -> GameConfig:
        raise NotImplementedError

    @abstractmethod
    async def save(self, game_config: GameConfig) -> GameConfig:
        raise NotImplementedError

