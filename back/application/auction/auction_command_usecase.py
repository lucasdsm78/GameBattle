from __future__ import annotations

import time

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import AuctionBidCommandModel, BlindtestBuzzerCommandModel, GameConfigReadModel


class AuctionCommandUseCase(GameConfigCommandBase):
    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    async def start(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_auction())

    async def register_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.register_auction_buzzer(payload.team.strip(), self._now_ms()))

    async def select_bid(self, payload: AuctionBidCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.select_auction_bid(payload.team.strip(), payload.target_count))

    async def launch(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.launch_auction_attempt(self._now_ms()))

    async def increment(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.change_auction_count(1, self._now_ms()))

    async def decrement(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.change_auction_count(-1, self._now_ms()))

    async def expire(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.expire_auction_attempt(self._now_ms()))

    async def next_theme(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.next_auction_theme())

