from __future__ import annotations

from abc import ABC, abstractmethod

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.repository.game_config_repository import GameConfigRepository


class GameConfigQueryUseCase(ABC):
    @abstractmethod
    async def get_current(self) -> GameConfigReadModel:
        raise NotImplementedError


class GameConfigQueryUseCaseImpl(GameConfigQueryUseCase):
    def __init__(self, repository: GameConfigRepository) -> None:
        self.repository = repository

    async def get_current(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        return GameConfigReadModel.from_domain(current)

