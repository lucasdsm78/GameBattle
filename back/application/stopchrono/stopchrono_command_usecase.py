from __future__ import annotations

import time

from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import GameConfigReadModel


class StopchronoCommandUseCase(GameConfigCommandBase):
    """Commandes du jeu Stopchrono : démarrage/arrêt du chrono et rotation des équipes."""

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    async def start(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.start_chrono(self._now_ms()))

    async def stop(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.stop_chrono(self._now_ms()))

    async def next_team(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.next_chrono_team())
