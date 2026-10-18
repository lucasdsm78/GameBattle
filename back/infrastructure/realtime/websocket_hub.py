from __future__ import annotations

import asyncio
from collections import deque
from contextlib import suppress
import json
import logging
from typing import Any, Optional

from fastapi import WebSocket

from application.game_config.snapshot import ClientRole, GameConfigSnapshot

logger = logging.getLogger(__name__)

SEND_TIMEOUT_SECONDS = 5.0
MAX_PENDING_REPLIES = 32


def encode_message(message: dict[str, Any]) -> str:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"))


def encode_snapshot(event_type: str, snapshot: GameConfigSnapshot, role: ClientRole) -> str:
    return encode_message({"type": event_type, "payload": snapshot.for_role(role)})


class ClientChannel:
    """File d'envoi d'un client : réponses directes dans l'ordre, puis le dernier état connu.

    Un état n'écrase que des états plus anciens (révision croissante) : un client lent saute les
    états intermédiaires au lieu de ralentir les autres, et ne reçoit jamais un état périmé.
    """

    def __init__(self, websocket: WebSocket, role: ClientRole) -> None:
        self.websocket = websocket
        self.role = role
        self._replies: deque[str] = deque(maxlen=MAX_PENDING_REPLIES)
        self._snapshot: Optional[str] = None
        self._revision = 0
        self._wakeup = asyncio.Event()
        self._task = asyncio.create_task(self._pump(), name=f"ws-{role}-pump")

    def push_reply(self, message: dict[str, Any]) -> None:
        self._replies.append(encode_message(message))
        self._wakeup.set()

    def push_snapshot(self, revision: int, encoded: str) -> None:
        if revision <= self._revision:
            return
        self._revision = revision
        self._snapshot = encoded
        self._wakeup.set()

    async def close(self) -> None:
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task

    async def _pump(self) -> None:
        try:
            while True:
                await self._wakeup.wait()
                self._wakeup.clear()
                while self._replies or self._snapshot is not None:
                    if self._replies:
                        text = self._replies.popleft()
                    else:
                        text, self._snapshot = self._snapshot, None
                    await asyncio.wait_for(self.websocket.send_text(text), SEND_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.info("websocket.client.dropped", extra={"client_type": self.role})
            with suppress(Exception):
                await self.websocket.close(code=1011)


class WebSocketHub:
    """Implémente `SnapshotPublisher` : diffusion non bloquante vers tous les clients connectés."""

    def __init__(self) -> None:
        self._channels: set[ClientChannel] = set()

    def connect(self, websocket: WebSocket, role: ClientRole) -> ClientChannel:
        channel = ClientChannel(websocket, role)
        self._channels.add(channel)
        return channel

    async def disconnect(self, channel: ClientChannel) -> None:
        self._channels.discard(channel)
        await channel.close()

    def publish(self, snapshot: GameConfigSnapshot) -> None:
        encoded: dict[ClientRole, str] = {}
        for channel in self._channels:
            if channel.role not in encoded:
                encoded[channel.role] = encode_snapshot("game.config.updated", snapshot, channel.role)
            channel.push_snapshot(snapshot.revision, encoded[channel.role])
