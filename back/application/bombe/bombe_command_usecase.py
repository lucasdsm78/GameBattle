from __future__ import annotations

import time

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import BombeBuzzerCommandModel, GameConfigReadModel


class BombeCommandUseCase(GameConfigCommandBase):
    """Commandes applicatives de La Bombe."""

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    async def start(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_bombe(self._now_ms()))

    async def register_buzzer(self, payload: BombeBuzzerCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.register_bombe_buzzer(payload.team.strip(), self._now_ms()))

    async def begin_after_roll(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.begin_bombe_after_roll(self._now_ms()))

    async def previous_team(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.previous_bombe_team(self._now_ms()))

    async def explode(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.explode_bombe(self._now_ms()))
