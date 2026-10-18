from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from application.commands.session import SessionCommandUseCase

logger = logging.getLogger(__name__)


class GameDeadlineWorker:
    """Clôt les chronos serveur échus (L’Enchère, Le mot interdit) sans dépendre d'un client connecté.

    Un tick sans chrono échu ne touche ni la base (dépôt en cache) ni le réseau.
    """

    def __init__(self, session: SessionCommandUseCase, *, poll_interval_seconds: float = 0.25) -> None:
        self._session = session
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
        return await self._session.expire_due_deadlines() is not None

    async def _run(self) -> None:
        while True:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("game.deadline_worker.failed")
            await asyncio.sleep(self._poll_interval_seconds)
