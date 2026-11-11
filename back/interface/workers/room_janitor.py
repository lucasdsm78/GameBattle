from __future__ import annotations

import time

from application.rooms.room_command_usecase import RoomCommandUseCase
from infrastructure.database.outbox.outbox_store import OutboxStore
from infrastructure.runtime.periodic_task import PeriodicTask
from interface.workers.constants.worker_schedules import PUBLISHED_EVENTS_KEPT_MS, ROOM_JANITOR_INTERVAL_SECONDS


class RoomJanitor(PeriodicTask):
    """Toutes les 10 minutes : ferme les salons abandonnés et vide l'outbox des événements déjà publiés."""

    name = "rooms.janitor"

    def __init__(self, rooms: RoomCommandUseCase, outbox: OutboxStore, *, interval_seconds: float = ROOM_JANITOR_INTERVAL_SECONDS) -> None:
        super().__init__(interval_seconds=interval_seconds)
        self._rooms = rooms
        self._outbox = outbox

    async def run_once(self) -> None:
        await self._rooms.purge_inactive()
        await self._outbox.purge_published(int(time.time() * 1000) - PUBLISHED_EVENTS_KEPT_MS)
