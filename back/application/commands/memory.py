from __future__ import annotations

from application.commands.base import CommandUseCase
from application.services.snapshot import GameConfigSnapshot


class MemoryCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_memory())

    async def next_question(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.next_memory_question())

    async def validate_sequence(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.validate_memory_sequence())

    async def disqualify_team(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.disqualify_memory_team())
