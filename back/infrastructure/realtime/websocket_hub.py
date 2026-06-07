from __future__ import annotations

import asyncio
from dataclasses import dataclass

from fastapi import WebSocket


@dataclass(slots=True, frozen=True)
class WebSocketClient:
    websocket: WebSocket
    client_type: str


class WebSocketHub:
    def __init__(self) -> None:
        self._clients: set[WebSocketClient] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_type: str) -> WebSocketClient:
        client = WebSocketClient(websocket=websocket, client_type=client_type)
        async with self._lock:
            self._clients.add(client)
        return client

    async def disconnect(self, client: WebSocketClient) -> None:
        async with self._lock:
            self._clients.discard(client)

    async def broadcast_json(self, message: dict) -> None:
        async with self._lock:
            clients = list(self._clients)

        stale_clients: list[WebSocketClient] = []
        for client in clients:
            try:
                await client.websocket.send_json(message)
            except Exception:
                stale_clients.append(client)

        if stale_clients:
            async with self._lock:
                for client in stale_clients:
                    self._clients.discard(client)

