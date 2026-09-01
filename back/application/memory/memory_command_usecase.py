from __future__ import annotations

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import GameConfigReadModel


class MemoryCommandUseCase(GameConfigCommandBase):
    """Commandes applicatives de Mémoire en chaîne."""

    async def start(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_memory())

    async def validate_answer(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.validate_memory_answer())

    async def disqualify_team(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.disqualify_memory_team())
