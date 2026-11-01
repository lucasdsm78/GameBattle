from __future__ import annotations

from application.fair_price.fair_price_commands import FairPriceFoundCommand, FairPriceHintCommand
from application.shared.command_usecase import CommandUseCase
from application.shared.snapshot import GameConfigSnapshot


class FairPriceCommandUseCase(CommandUseCase):
    async def start_turn(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_fair_price_turn(ctx.now_ms))

    async def give_hint(self, command: FairPriceHintCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.give_fair_price_hint(command.direction, command.proposals, ctx.now_ms))

    async def mark_found(self, command: FairPriceFoundCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.mark_fair_price_found(command.proposals, ctx.now_ms))
