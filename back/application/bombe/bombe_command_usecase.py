from __future__ import annotations

from application.shared.command_usecase import CommandUseCase
from application.shared.commands import TeamCommand
from application.shared.snapshot import GameConfigSnapshot


class BombeCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_bombe(ctx.now_ms))

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_bombe_buzzer(command.team, ctx.now_ms))

    async def begin_after_roll(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.begin_bombe_after_roll(ctx.now_ms))

    async def previous_team(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.previous_bombe_team(ctx.now_ms))

    async def explode(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.explode_bombe(ctx.now_ms))
