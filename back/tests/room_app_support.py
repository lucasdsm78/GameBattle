from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import pytest
from account_support import PASSWORD, build_use_case
from fastapi import FastAPI
from fastapi.testclient import TestClient
from room_support import InMemoryOutboxStore, RoomsHarness, build_rooms

from infrastructure.config import Settings
from interface import http_session
from interface.api import accounts as accounts_api
from interface.api import room_realtime
from interface.api import rooms as rooms_api
from interface.dependencies.container import account_usecase, room_broadcaster, room_command_usecase, room_hub, room_query_usecase
from interface.errors import register_exception_handlers
from interface.realtime.room_broadcaster import RoomBroadcaster
from interface.realtime.room_hub import RoomHub
from interface.workers.outbox_relay import OutboxRelay
from interface.workers.relay_notifier import RelayNotifier

ORIGIN = "http://testserver"


@dataclass
class RoomApp:
    """Une app réduite aux comptes et aux salons, en mémoire, avec le vrai relais d'outbox et le vrai hub."""

    client: TestClient
    rooms: RoomsHarness
    hub: RoomHub

    def register(self, pseudo: str) -> dict[str, str]:
        """Inscrit un joueur et renvoie ses en-têtes : chacun garde son cookie, sur un même client (une même boucle)."""
        response = self.client.post("/api/accounts/register", json={"pseudo": pseudo, "password": PASSWORD}, headers={"Origin": ORIGIN})
        assert response.status_code == 201, response.text
        token = response.cookies["gb_session"]
        self.client.cookies.clear()
        return {"Origin": ORIGIN, "Cookie": f"gb_session={token}"}


@contextmanager
def running_room_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[RoomApp]:
    settings = Settings(_env_file=None, environment="development", rate_limit_secret="r" * 64)
    for module in (accounts_api, http_session):
        monkeypatch.setattr(module, "get_settings", lambda: settings)

    relay_holder: list[OutboxRelay] = []
    rooms = build_rooms(relay=RelayNotifier(lambda: relay_holder[0]))
    hub = RoomHub()
    broadcaster = RoomBroadcaster(rooms.queries, hub)
    relay = OutboxRelay(InMemoryOutboxStore(rooms.store), broadcaster, interval_seconds=0.05)
    relay_holder.append(relay)
    accounts, _, _ = build_use_case()

    app = FastAPI()
    register_exception_handlers(app)
    for router in (accounts_api.router, rooms_api.router, room_realtime.router):
        app.include_router(router)
    app.dependency_overrides.update(
        {account_usecase: lambda: accounts, room_command_usecase: lambda: rooms.commands,
            room_query_usecase: lambda: rooms.queries,
            room_hub: lambda: hub, room_broadcaster: lambda: broadcaster}
    )
    with TestClient(app, base_url=ORIGIN) as client:
        assert client.portal is not None
        client.portal.call(relay.start)
        try:
            yield RoomApp(client, rooms, hub)
        finally:
            client.portal.call(relay.stop)
