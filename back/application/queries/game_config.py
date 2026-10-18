from __future__ import annotations

from application.services.snapshot import GameConfigSnapshot
from domain.repositories.game_config import GameConfigRepository


class GameConfigQueryService:
    def __init__(self, repository: GameConfigRepository) -> None:
        self._repository = repository

    async def get_current(self) -> GameConfigSnapshot:
        async with self._repository.mutation_lock:
            return GameConfigSnapshot.from_domain(await self._repository.get_current())
