from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket

from interface.realtime.room_connection import RoomConnection

MAX_CONNECTIONS_PER_PLAYER = 3  # onglets ou appareils ouverts sur le même salon


class RoomHub:
    """Les connexions ouvertes, rangées par salon. Mono-processus, comme le reste de l'API (`SingleInstanceLock`)."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[RoomConnection]] = defaultdict(set)

    def connect(self, websocket: WebSocket, room_id: str, account_id: str) -> RoomConnection:
        mine = sorted((c for c in self._rooms[room_id] if c.account_id == account_id), key=lambda c: c.opened_at)
        for oldest in mine[: max(0, len(mine) - MAX_CONNECTIONS_PER_PLAYER + 1)]:
            self._rooms[room_id].discard(oldest)
            asyncio.create_task(oldest.close(4000, "remplacée par une connexion plus récente"))
        connection = RoomConnection(websocket, room_id, account_id)
        self._rooms[room_id].add(connection)
        return connection

    def remove(self, connection: RoomConnection) -> None:
        """Synchrone : la connexion sort du salon même si la tâche qui la porte est en train d'être annulée."""
        connections = self._rooms.get(connection.room_id)
        if connections is not None:
            connections.discard(connection)
            if not connections:
                del self._rooms[connection.room_id]

    async def disconnect(self, connection: RoomConnection) -> None:
        self.remove(connection)
        await connection.close()

    def connections(self, room_id: str) -> list[RoomConnection]:
        return list(self._rooms.get(room_id, ()))

    def online(self, room_id: str) -> frozenset[str]:
        return frozenset(connection.account_id for connection in self._rooms.get(room_id, ()) if not connection.closed)
