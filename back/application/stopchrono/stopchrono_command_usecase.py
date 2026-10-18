from __future__ import annotations

from application.shared.command_usecase import CommandUseCase
from application.shared.snapshot import GameConfigSnapshot


class StopChronoCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_chrono(ctx.now_ms))

    async def stop(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.stop_chrono(ctx.now_ms))

    async def next_team(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.next_chrono_team())
