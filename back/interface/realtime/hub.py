from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from contextlib import suppress
from typing import Any, Optional

from fastapi import WebSocket

from application.services.snapshot import ClientRole, GameConfigSnapshot

logger = logging.getLogger(__name__)

SEND_TIMEOUT_SECONDS = 5.0
MAX_PENDING_REPLIES = 32


def encode_message(message: dict[str, Any]) -> str:
    return json.dumps(message, ensure_ascii=False, separators=(",", ":"))


MAX_PENDING_EVENTS = 200


def encode_payload(snapshot: GameConfigSnapshot, role: ClientRole) -> str:
    return encode_message(snapshot.for_role(role))


def compose_state_message(event_type: str, payload_json: str, events: list[dict[str, Any]]) -> str:
    # Composition par chaînes : la vue (volumineuse) n'est encodée qu'une fois par rôle, pas par client.
    return f'{{"type":{encode_message(event_type)},"payload":{payload_json},"events":{encode_message(events)}}}'


class ClientChannel:
    """File d'envoi d'un client : réponses directes dans l'ordre, puis le dernier état connu.

    Un état n'écrase que des états plus anciens (révision croissante) : un client lent saute les
    états intermédiaires au lieu de ralentir les autres, et ne reçoit jamais un état périmé. Les
    événements de domaine, eux, ne sont jamais sautés : ils s'accumulent et partent avec l'état suivant.
    """

    def __init__(self, websocket: WebSocket, role: ClientRole) -> None:
        self.websocket = websocket
        self.role = role
        self._replies: deque[str] = deque(maxlen=MAX_PENDING_REPLIES)
        self._state: Optional[tuple[str, str]] = None
        self._events: deque[dict[str, Any]] = deque(maxlen=MAX_PENDING_EVENTS)
        self._revision = 0
        self._wakeup = asyncio.Event()
        self._task = asyncio.create_task(self._pump(), name=f"ws-{role}-pump")

    def push_reply(self, message: dict[str, Any]) -> None:
        self._replies.append(encode_message(message))
        self._wakeup.set()

    def push_state(self, revision: int, event_type: str, payload_json: str, events: tuple[dict[str, Any], ...] = ()) -> None:
        if revision <= self._revision:
            return
        self._revision = revision
        self._state = (event_type, payload_json)
        self._events.extend(events)
        self._wakeup.set()

    def _next_message(self) -> Optional[str]:
        if self._replies:
            return self._replies.popleft()
        if self._state is None:
            return None
        (event_type, payload_json), self._state = self._state, None
        events = list(self._events)
        self._events.clear()
        return compose_state_message(event_type, payload_json, events)

    async def close(self) -> None:
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task

    async def _pump(self) -> None:
        try:
            while True:
                await self._wakeup.wait()
                self._wakeup.clear()
                while (text := self._next_message()) is not None:
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
                encoded[channel.role] = encode_payload(snapshot, channel.role)
            channel.push_state(snapshot.revision, "game.config.updated", encoded[channel.role], snapshot.events)
