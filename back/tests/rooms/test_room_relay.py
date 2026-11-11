from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from fastapi import WebSocket
from room_support import ALICE, BOB, CHLOE, IP, InMemoryOutboxStore, build_rooms

from application.rooms.commands.create_room import CreateRoomCommand
from application.rooms.commands.join_room import JoinRoomCommand
from interface.realtime.room_broadcaster import RoomBroadcaster, RoomEvent
from interface.realtime.room_hub import MAX_CONNECTIONS_PER_PLAYER, RoomHub
from interface.workers import outbox_relay
from interface.workers.outbox_relay import OutboxRelay


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed_with: int | None = None

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed_with = code

    def types(self) -> list[str]:
        return [json.loads(text)["type"] for text in self.sent]

    def last(self) -> dict[str, Any]:
        return json.loads(self.sent[-1])


def _socket(fake: FakeSocket) -> WebSocket:
    return cast(WebSocket, fake)


def test_the_hub_keeps_at_most_three_tabs_per_player() -> None:
    async def scenario() -> None:
        hub, sockets = RoomHub(), [FakeSocket() for _ in range(MAX_CONNECTIONS_PER_PLAYER + 1)]
        for fake in sockets:
            hub.connect(_socket(fake), "room", ALICE.account_id)
            await asyncio.sleep(0)
        await asyncio.sleep(0.01)

        assert len(hub.connections("room")) == MAX_CONNECTIONS_PER_PLAYER and hub.online("room") == {ALICE.account_id}
        assert sockets[0].closed_with == 4000 and all(fake.closed_with is None for fake in sockets[1:])
        for connection in hub.connections("room"):
            await hub.disconnect(connection)
        assert hub.connections("room") == [] and hub.online("room") == frozenset()

    asyncio.run(scenario())


def test_private_events_only_reach_their_audience() -> None:
    async def scenario() -> None:
        rooms = build_rooms()
        view = await rooms.use_case.create(ALICE, CreateRoomCommand(visibility="public", format="teams"))
        await rooms.use_case.join_public(BOB, view["id"])
        hub = RoomHub()
        alice_socket, bob_socket = FakeSocket(), FakeSocket()
        hub.connect(_socket(alice_socket), view["id"], ALICE.account_id)
        hub.connect(_socket(bob_socket), view["id"], BOB.account_id)

        await RoomBroadcaster(rooms.use_case, hub).broadcast(
            view["id"], [RoomEvent("room.notice", {"text": "pour Bob"}, audience=BOB.account_id), RoomEvent("room.notice", {"text": "pour tous"})]
        )
        await asyncio.sleep(0.01)

        assert [event["text"] for event in alice_socket.last()["events"]] == ["pour tous"]
        assert [event["text"] for event in bob_socket.last()["events"]] == ["pour Bob", "pour tous"]
        assert alice_socket.last()["room"]["me"]["pseudo"] == "Alice" and bob_socket.last()["room"]["me"]["pseudo"] == "Bob"

    asyncio.run(scenario())


def test_the_relay_publishes_each_room_once_then_marks_its_events() -> None:
    async def scenario() -> None:
        rooms = build_rooms()
        first = await rooms.use_case.create(ALICE, CreateRoomCommand(visibility="private", format="teams"))
        second = await rooms.use_case.create(CHLOE, CreateRoomCommand(visibility="public", format="solo"))
        await rooms.use_case.join_by_invitation(BOB, first["invite_path"].rsplit("/", 1)[1], JoinRoomCommand(), IP)
        hub, store = RoomHub(), InMemoryOutboxStore(rooms.store)
        alice_socket, chloe_socket = FakeSocket(), FakeSocket()
        hub.connect(_socket(alice_socket), first["id"], ALICE.account_id)
        hub.connect(_socket(chloe_socket), second["id"], CHLOE.account_id)
        relay = OutboxRelay(store, RoomBroadcaster(rooms.use_case, hub))

        assert await relay.run_once() == 5
        await asyncio.sleep(0.01)
        assert [event["type"] for event in alice_socket.last()["events"]] == ["room.opened", "room.player_joined", "room.player_joined"]
        assert alice_socket.types() == ["room.updated"] and chloe_socket.types() == ["room.updated"]
        assert await relay.run_once() == 0 and len(alice_socket.sent) == 1  # déjà publiés : rien ne repart

    asyncio.run(scenario())


def test_a_full_batch_wakes_the_relay_again(monkeypatch: Any) -> None:
    async def scenario() -> None:
        monkeypatch.setattr(outbox_relay, "RELAY_BATCH", 2)
        rooms = build_rooms()
        await rooms.use_case.create(ALICE, CreateRoomCommand(visibility="public", format="solo"))
        relay = OutboxRelay(InMemoryOutboxStore(rooms.store), RoomBroadcaster(rooms.use_case, RoomHub()))
        woken: list[bool] = []
        monkeypatch.setattr(relay, "wake", lambda: woken.append(True))

        assert await relay.run_once() == 2 and woken == [True]
        assert await relay.run_once() == 0 and woken == [True]

    asyncio.run(scenario())
