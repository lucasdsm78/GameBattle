from __future__ import annotations

import time

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import (
    BlindtestBuzzerCommandModel,
    GameConfigReadModel,
    SevenDifferenceFoundCommandModel,
)


class SevenDifferencesCommandUseCase(GameConfigCommandBase):
    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    async def start(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_seven_differences(self._now_ms()))

    async def open(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.open_seven_differences(self._now_ms()))

    async def register_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        return await self._mutate(
            lambda config: config.register_seven_differences_buzzer(payload.team.strip(), self._now_ms())
        )

    async def mark_found(self, payload: SevenDifferenceFoundCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.find_seven_difference(payload.difference_id))

    async def reject_answer(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.reject_seven_differences_answer())
