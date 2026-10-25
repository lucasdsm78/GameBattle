from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from application.game_night.game_night_command_usecase import GameNightCommandUseCase

logger = logging.getLogger(__name__)


class GameDeadlineWorker:
    """Fait avancer les chronos serveur échus (L’Enchère, Le mot interdit, Le mot qui disparaît, Calcul flash, Le bon drapeau) sans dépendre d'un client connecté.

    Un tick sans chrono échu ne touche ni la base (dépôt en cache) ni le réseau.
    """

    def __init__(self, game_night: GameNightCommandUseCase, *, poll_interval_seconds: float = 0.25) -> None:
        self._game_night = game_night
        self._poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="game-deadline-worker")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def check_once(self) -> bool:
        return await self._game_night.expire_due_deadlines() is not None

    async def _run(self) -> None:
        while True:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("game.deadline_worker.failed")
            await asyncio.sleep(self._poll_interval_seconds)
