from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from contextlib import suppress
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

MAX_PENDING_MESSAGES = 64  # au-delà, le client est trop en retard : on le coupe, il se resynchronisera
SEND_TIMEOUT_SECONDS = 5.0


class RoomConnection:
    """Une connexion d'un joueur à son salon, avec sa propre file d'envoi : un client lent ne ralentit personne."""

    def __init__(self, websocket: WebSocket, room_id: str, account_id: str) -> None:
        self.websocket = websocket
        self.room_id = room_id
        self.account_id = account_id
        self.opened_at = self.last_seen = time.monotonic()
        self.closed = False
        self._queue: deque[str] = deque()
        self._wakeup = asyncio.Event()
        self._drained = asyncio.Event()
        self._drained.set()
        self._pump_task = asyncio.create_task(self._pump(), name=f"room-socket-{room_id}")

    def send(self, message: dict[str, Any]) -> None:
        if self.closed:
            return
        if len(self._queue) >= MAX_PENDING_MESSAGES:
            asyncio.create_task(self.close(1013, "trop de retard"))
            return
        self._queue.append(json.dumps(message, ensure_ascii=False, separators=(",", ":")))
        self._drained.clear()
        self._wakeup.set()

    async def flush_and_close(self, code: int, reason: str) -> None:
        """Laisse partir les messages en file (ex. « tu as quitté le salon »), puis ferme."""
        with suppress(TimeoutError):
            await asyncio.wait_for(self._drained.wait(), SEND_TIMEOUT_SECONDS)
        await self.close(code, reason)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        if self.closed:
            return
        self.closed = True
        self._pump_task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await self._pump_task
        with suppress(Exception):
            await self.websocket.close(code=code, reason=reason)

    async def _pump(self) -> None:
        try:
            while True:
                await self._wakeup.wait()
                self._wakeup.clear()
                while self._queue:
                    await asyncio.wait_for(self.websocket.send_text(self._queue.popleft()), SEND_TIMEOUT_SECONDS)
                self._drained.set()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.info("room.socket.dropped", extra={"room_id": self.room_id})
            self.closed = True
            with suppress(Exception):
                await self.websocket.close(code=1011)
