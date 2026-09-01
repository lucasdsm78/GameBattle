from __future__ import annotations

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import GameConfigReadModel


class MemoryCommandUseCase(GameConfigCommandBase):
    """Commandes applicatives de Mémoire en chaîne."""

    async def start(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_memory())

    async def next_question(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.next_memory_question())

    async def validate_sequence(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.validate_memory_sequence())

    async def disqualify_team(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.disqualify_memory_team())
