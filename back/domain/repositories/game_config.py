from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from domain.models.game_config import GameConfig


class GameConfigRepository(ABC):
    @property
    def mutation_lock(self) -> asyncio.Lock:
        """Verrou commun à toutes les écritures partageant ce dépôt (recréé si la boucle asyncio change)."""
        current_loop = asyncio.get_running_loop()
        lock = getattr(self, "_mutation_lock", None)
        if lock is None or getattr(self, "_mutation_lock_loop", None) is not current_loop:
            lock = asyncio.Lock()
            self._mutation_lock = lock
            self._mutation_lock_loop = current_loop
        return lock

    @abstractmethod
    async def get_current(self) -> GameConfig: ...

    @abstractmethod
    async def save(self, game_config: GameConfig) -> GameConfig: ...
