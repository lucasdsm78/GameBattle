from __future__ import annotations

from application.shared.command_usecase import CommandUseCase
from application.shared.commands import TeamCommand
from application.shared.snapshot import GameConfigSnapshot


class RightFlagCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_right_flag(ctx.now_ms))

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_right_flag_buzzer(command.team, ctx.now_ms))

    async def pause(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.pause_right_flag())

    async def resume(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.resume_right_flag(ctx.now_ms))
