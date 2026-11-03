from __future__ import annotations

from application.game_night.game_night_command_usecase import GameNightCommandUseCase
from interface.periodic_task import PeriodicTask


class GameDeadlineWorker(PeriodicTask):
    """Fait avancer les chronos serveur échus (L’Enchère, Le mot interdit, Le mot qui disparaît, Calcul flash, Le bon drapeau, Le juste prix) sans dépendre d'un client connecté.

    Un tick sans chrono échu ne touche ni la base (dépôt en cache) ni le réseau.
    """

    name = "game.deadline_worker"

    def __init__(self, game_night: GameNightCommandUseCase, *, poll_interval_seconds: float = 0.25) -> None:
        super().__init__(interval_seconds=poll_interval_seconds)
        self._game_night = game_night

    async def check_once(self) -> bool:
        return await self._game_night.expire_due_deadlines() is not None

    async def run_once(self) -> bool:
        return await self.check_once()
