from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

from application.rooms.presenters.room_view import room_view
from application.rooms.room_query_usecase import RoomQueryUseCase
from interface.realtime.room_connection import RoomConnection
from interface.realtime.room_hub import RoomHub

logger = logging.getLogger(__name__)

LEFT_ROOM_CODE = 4000  # fermeture normale : le joueur n'est plus membre (parti, ou salon fermé)


@dataclass(frozen=True, slots=True)
class RoomEvent:
    type: str
    payload: dict[str, Any]
    audience: Optional[str] = None  # compte destinataire d'un événement privé ; `None` : tout le salon

    def as_message(self) -> dict[str, Any]:
        return {"type": self.type, **self.payload}


class RoomBroadcaster:
    """Envoie à chaque connexion d'un salon l'état complet tel que la voit son joueur, plus les événements récents.

    Les clients remplacent leur état à chaque message (resynchronisation complète, `version` croissante) : un
    message perdu ou rejoué ne laisse jamais d'état incohérent. Un événement privé ne part qu'à son destinataire.
    """

    def __init__(self, rooms: RoomQueryUseCase, hub: RoomHub) -> None:
        self._rooms = rooms
        self._hub = hub
        self._background: set[asyncio.Task[None]] = set()

    def broadcast_soon(self, room_id: str) -> None:
        """Diffusion détachée de l'appelant : une connexion qui se termine (ou s'annule) n'emporte pas la mise à jour de présence."""
        task = asyncio.create_task(self._broadcast_logged(room_id), name=f"room-presence-{room_id}")
        self._background.add(task)  # référence forte : une tâche sans référence peut être ramassée en cours de route
        task.add_done_callback(self._background.discard)

    async def broadcast(self, room_id: str, events: Sequence[RoomEvent] = ()) -> None:
        connections = self._hub.connections(room_id)
        if not connections:
            return
        room = await self._rooms.get_room(room_id)
        leaving: list[RoomConnection] = []
        if room is None or room.status == "closed":
            for connection in connections:
                connection.send({"type": "room.closed"})
                leaving.append(connection)
        else:
            online = self._hub.online(room_id)
            for connection in connections:
                if room.member(connection.account_id) is None:  # parti entre-temps : on le prévient puis on coupe
                    connection.send({"type": "room.left"})
                    leaving.append(connection)
                    continue
                connection.send(
                    {
                        "type": "room.updated",
                        "room": room_view(room, connection.account_id, online),
                        "events": [event.as_message() for event in events if event.audience in (None, connection.account_id)],
                    }
                )
        # Tout le monde est servi d'abord ; les départs se ferment ensuite, en parallèle.
        await asyncio.gather(*(self._close(connection) for connection in leaving))

    async def _broadcast_logged(self, room_id: str) -> None:
        try:
            await self.broadcast(room_id)
        except Exception:  # personne n'attend cette tâche : on journalise au lieu de perdre l'erreur
            logger.exception("room.presence.broadcast_failed", extra={"room_id": room_id})

    async def _close(self, connection: RoomConnection) -> None:
        await connection.flush_and_close(LEFT_ROOM_CODE, "plus membre du salon")
        await self._hub.disconnect(connection)
