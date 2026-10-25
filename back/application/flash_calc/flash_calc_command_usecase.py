from __future__ import annotations

from application.shared.command_usecase import CommandUseCase
from application.shared.commands import TeamCommand
from application.shared.snapshot import GameConfigSnapshot


class FlashCalcCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_flash_calc(ctx.now_ms))

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_flash_calc_buzzer(command.team, ctx.now_ms))

    async def pause(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.pause_flash_calc())

    async def resume(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.resume_flash_calc(ctx.now_ms))
