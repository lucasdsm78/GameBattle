from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from application.game_config.command import GameConfigCommandUseCase
from infrastructure.realtime.websocket_hub import WebSocketHub
from presentation.realtime.game_config_ws_handler import build_broadcast_envelopes

logger = logging.getLogger(__name__)


class GameDeadlineWorker:
    """Clôt les chronos serveur échus (L’Enchère, Le mot interdit) sans dépendre d'un client connecté.

    Un tick sans chrono échu ne persiste ni ne diffuse rien.
    """

    def __init__(
        self,
        command_usecase: GameConfigCommandUseCase,
        hub: WebSocketHub,
        *,
        poll_interval_seconds: float = 0.25,
    ) -> None:
        self._command_usecase = command_usecase
        self._hub = hub
        self._poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="game-deadline-worker")

    async def stop(self) -> None:
        if not self._task:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def check_once(self) -> bool:
        updated = await self._command_usecase.expire_due_deadline()
        if updated is None:
            return False
        await self._hub.broadcast_json_by_client_type(
            build_broadcast_envelopes("game.config.updated", updated)
        )
        return True

    async def _run(self) -> None:
        while True:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("game.deadline_worker.failed")
            await asyncio.sleep(self._poll_interval_seconds)
