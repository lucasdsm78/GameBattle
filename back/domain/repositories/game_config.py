from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models.game_config import GameConfig


class GameConfigRepository(ABC):
    @abstractmethod
    async def get_current(self) -> GameConfig: ...

    @abstractmethod
    async def save(self, game_config: GameConfig) -> GameConfig: ...
