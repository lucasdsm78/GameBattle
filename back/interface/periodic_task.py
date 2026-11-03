from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import ClassVar

logger = logging.getLogger(__name__)


class PeriodicTask(ABC):
    """Tâche de fond relancée à intervalle fixe ; une erreur est journalisée sans arrêter la boucle."""

    name: ClassVar[str]

    def __init__(self, *, interval_seconds: float) -> None:
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None

    @abstractmethod
    async def run_once(self) -> object: ...

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name=self.name)

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("%s.failed", self.name)
            await asyncio.sleep(self._interval_seconds)
