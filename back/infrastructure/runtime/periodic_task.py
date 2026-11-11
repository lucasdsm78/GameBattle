from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import suppress
from typing import ClassVar

logger = logging.getLogger(__name__)

RETRY_FIRST_DELAY_SECONDS = 1.0
STOP_GRACE_SECONDS = 5.0


class PeriodicTask(ABC):
    """Tâche de fond relancée à intervalle fixe.

    Une erreur ne casse pas la boucle : la tâche réessaie vite (1 s, 2 s, 4 s… plafonné à l'intervalle normal)
    au lieu d'attendre un intervalle complet, et chaque échec est journalisé avec le nombre d'échecs d'affilée.
    L'arrêt est gracieux : le passage en cours se termine (une transaction n'est jamais coupée en deux) ; il
    n'est annulé qu'au-delà de `STOP_GRACE_SECONDS`.
    """

    name: ClassVar[str]
    wakeable: ClassVar[bool] = False  # vrai : `wake()` relance un passage sans attendre la fin de l'intervalle

    def __init__(self, *, interval_seconds: float) -> None:
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._stopping: asyncio.Event | None = None
        self._wakeup: asyncio.Event | None = None
        self.consecutive_failures = 0

    @abstractmethod
    async def run_once(self) -> object: ...

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopping = asyncio.Event()
            self._wakeup = asyncio.Event() if self.wakeable else None
            self._task = asyncio.create_task(self._run(self._stopping), name=self.name)

    def wake(self) -> None:
        if self._wakeup is not None:
            self._wakeup.set()

    async def stop(self) -> None:
        if self._task is None or self._stopping is None:
            return
        self._stopping.set()
        try:
            await asyncio.wait_for(asyncio.shield(self._task), STOP_GRACE_SECONDS)
        except TimeoutError:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    def next_delay_seconds(self) -> float:
        if not self.consecutive_failures:
            return self._interval_seconds
        return min(self._interval_seconds, RETRY_FIRST_DELAY_SECONDS * 2 ** (self.consecutive_failures - 1))

    async def tick(self) -> None:
        """Un passage : en cas d'erreur, on compte l'échec (le prochain délai raccourcit) au lieu de lever."""
        try:
            await self.run_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            self.consecutive_failures += 1
            logger.exception(
                "%s.failed consecutive_failures=%d retry_in=%.0fs",
                self.name,
                self.consecutive_failures,
                self.next_delay_seconds(),
                extra={"task": self.name, "consecutive_failures": self.consecutive_failures},
            )
            return
        if self.consecutive_failures:
            logger.info(
                "%s.recovered after_failures=%d",
                self.name,
                self.consecutive_failures,
                extra={"task": self.name, "after_failures": self.consecutive_failures},
            )
        self.consecutive_failures = 0

    async def _run(self, stopping: asyncio.Event) -> None:
        while not stopping.is_set():
            await self.tick()
            await self._pause(stopping)

    async def _pause(self, stopping: asyncio.Event) -> None:
        if self._wakeup is None:
            with suppress(TimeoutError):
                await asyncio.wait_for(stopping.wait(), self.next_delay_seconds())
            return
        waiters = {asyncio.ensure_future(stopping.wait()), asyncio.ensure_future(self._wakeup.wait())}
        _, pending = await asyncio.wait(waiters, timeout=self.next_delay_seconds(), return_when=asyncio.FIRST_COMPLETED)
        for waiter in pending:
            waiter.cancel()
        self._wakeup.clear()
