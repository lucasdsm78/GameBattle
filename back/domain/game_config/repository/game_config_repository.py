from __future__ import annotations

from abc import ABC, abstractmethod

from domain.game_config.model.game_config import GameConfig


class GameConfigRepository(ABC):
    @abstractmethod
    async def get_current(self) -> GameConfig:
        raise NotImplementedError

    @abstractmethod
    async def save(self, game_config: GameConfig) -> GameConfig:
        raise NotImplementedError

