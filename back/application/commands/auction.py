from __future__ import annotations

from application.commands.base import CommandUseCase
from application.commands.payloads import AuctionBidCommand, TeamCommand
from application.services.snapshot import GameConfigSnapshot


class AuctionCommandUseCase(CommandUseCase):
    async def start(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.start_auction())

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_auction_buzzer(command.team, ctx.now_ms))

    async def select_bid(self, command: AuctionBidCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.select_auction_bid(command.team, command.target_count))

    async def launch(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.launch_auction_attempt(ctx.now_ms))

    async def increment(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.change_auction_count(1, ctx.now_ms))

    async def decrement(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.change_auction_count(-1, ctx.now_ms))

    async def next_theme(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.next_auction_theme())
