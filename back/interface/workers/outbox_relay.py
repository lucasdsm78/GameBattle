from __future__ import annotations

import time
from collections import defaultdict

from infrastructure.database.outbox.outbox_store import OutboxStore
from infrastructure.runtime.periodic_task import PeriodicTask
from interface.realtime.room_broadcaster import RoomBroadcaster, RoomEvent
from interface.workers.constants.worker_schedules import RELAY_BATCH, RELAY_INTERVAL_SECONDS


class OutboxRelay(PeriodicTask):
    """Publie les événements validés de l'outbox, dans l'ordre, puis les marque publiés.

    Réveillé après chaque écriture (publication immédiate) ; à défaut, un passage par seconde rattrape tout ce
    qui reste (redémarrage, erreur réseau). Livraison « au moins une fois » : les clients remplacent leur état à
    chaque message, si bien qu'un événement rejoué ne fait aucun mal.
    """

    name = "outbox.relay"
    wakeable = True

    def __init__(self, store: OutboxStore, broadcaster: RoomBroadcaster, *, interval_seconds: float = RELAY_INTERVAL_SECONDS) -> None:
        super().__init__(interval_seconds=interval_seconds)
        self._store = store
        self._broadcaster = broadcaster

    async def run_once(self) -> int:
        pending = await self._store.pending(RELAY_BATCH)
        by_room: dict[str, list[RoomEvent]] = defaultdict(list)
        for event in pending:
            kind, _, identifier = event.stream.partition(":")
            if kind == "room":
                by_room[identifier].append(RoomEvent(event.event_type, event.payload, event.audience))
        for room_id, events in by_room.items():
            await self._broadcaster.broadcast(room_id, events)
        await self._store.mark_published([event.id for event in pending], int(time.time() * 1000))
        if len(pending) == RELAY_BATCH:
            self.wake()  # il en reste : on enchaîne sans attendre
        return len(pending)
