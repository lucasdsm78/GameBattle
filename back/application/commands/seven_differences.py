from __future__ import annotations

from application.commands.base import CommandUseCase
from application.commands.payloads import SevenDifferenceFoundCommand, TeamCommand
from application.services.snapshot import GameConfigSnapshot


class SevenDifferencesCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_seven_differences(ctx.now_ms))

    async def open(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.open_seven_differences(ctx.now_ms))

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_seven_differences_buzzer(command.team, ctx.now_ms))

    async def mark_found(self, command: SevenDifferenceFoundCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.find_seven_difference(command.difference_id))

    async def reject_answer(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.reject_seven_differences_answer())
