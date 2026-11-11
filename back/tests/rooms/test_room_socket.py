from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from room_app_support import ORIGIN, RoomApp
from starlette.testclient import WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from interface.dependencies.container import room_broadcaster
from interface.realtime.constants.websocket_codes import CLOSE_LEFT_ROOM, CLOSE_NOT_IN_ROOM, CLOSE_TOO_CHATTY, CLOSE_UNAUTHENTICATED

SOCKET = "/ws/rooms/current"
Message = dict[str, Any]


def _until(socket: WebSocketTestSession, matches: Callable[[Message], bool], *, limit: int = 10) -> Message:
    """Le premier message attendu : le relais peut livrer un état intermédiaire avant (au moins une fois, dans l'ordre)."""
    for _ in range(limit):
        message = socket.receive_json()
        if matches(message):
            return message
    raise AssertionError("message attendu jamais reçu")


def _closed_with(socket: WebSocketTestSession) -> int:
    with pytest.raises(WebSocketDisconnect) as closed:
        for _ in range(10):
            socket.receive_json()
    return closed.value.code


def _online(message: Message) -> dict[str, bool]:
    return {player["pseudo"]: player["online"] for player in message.get("room", {}).get("players", ())}


def _create(room_app: RoomApp, headers: dict[str, str], **body: Any) -> Message:
    response = room_app.client.post("/api/rooms", json={"visibility": "private", "format": "teams", **body}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_a_foreign_site_is_refused_before_the_handshake(room_app: RoomApp) -> None:
    alice = room_app.register("Alice")
    _create(room_app, alice)

    with pytest.raises(WebSocketDisconnect) as refused:
        with room_app.client.websocket_connect(SOCKET, headers=alice | {"Origin": "https://evil.example"}):
            pass
    assert refused.value.code == 1008


def test_without_session_or_room_the_socket_closes_with_an_explicit_code(room_app: RoomApp) -> None:
    alice = room_app.register("Alice")

    with room_app.client.websocket_connect(SOCKET, headers={"Origin": ORIGIN}) as anonymous:
        assert _closed_with(anonymous) == CLOSE_UNAUTHENTICATED
    with room_app.client.websocket_connect(SOCKET, headers=alice) as homeless:
        assert _closed_with(homeless) == CLOSE_NOT_IN_ROOM


def test_members_get_a_snapshot_then_live_updates_with_presence(room_app: RoomApp) -> None:
    alice, bob = room_app.register("Alice"), room_app.register("Bob")
    code = _create(room_app, alice)["invite_path"].rsplit("/", 1)[1]

    with room_app.client.websocket_connect(SOCKET, headers=alice) as alice_socket:
        snapshot = alice_socket.receive_json()
        assert snapshot["type"] == "room.snapshot" and _online(snapshot) == {"Alice": True}
        assert snapshot["room"]["me"]["is_host"] and "account_id" not in str(snapshot)

        room_app.client.post(f"/api/rooms/invitations/{code}/join", json={"team": "Bleus"}, headers=bob)
        joined = _until(alice_socket, lambda message: any(e["type"] == "room.player_joined" for e in message.get("events", ())))
        assert joined["type"] == "room.updated" and _online(joined) == {"Alice": True, "Bob": False}
        assert {"type": "room.player_joined", "pseudo": "Bob", "team": "Bleus"} in joined["events"]

        with room_app.client.websocket_connect(SOCKET, headers=bob) as bob_socket:
            assert bob_socket.receive_json()["room"]["me"]["team"] == "Bleus"
            _until(alice_socket, lambda message: _online(message).get("Bob") is True)
        _until(alice_socket, lambda message: _online(message).get("Bob") is False)  # parti : hors ligne pour les autres


def test_leaving_tells_the_player_then_closes_their_socket(room_app: RoomApp) -> None:
    alice, bob = room_app.register("Alice"), room_app.register("Bob")
    code = _create(room_app, alice)["invite_path"].rsplit("/", 1)[1]
    room_app.client.post(f"/api/rooms/invitations/{code}/join", headers=bob)

    with room_app.client.websocket_connect(SOCKET, headers=alice) as alice_socket, room_app.client.websocket_connect(SOCKET, headers=bob) as bob_socket:
        bob_socket.receive_json()
        assert room_app.client.post("/api/rooms/current/leave", headers=bob).status_code == 204

        assert _until(bob_socket, lambda message: message["type"] == "room.left") == {"type": "room.left"}
        assert _closed_with(bob_socket) == CLOSE_LEFT_ROOM
        left = _until(alice_socket, lambda message: any(e["type"] == "room.player_left" for e in message.get("events", ())))
        assert [player["pseudo"] for player in left["room"]["players"]] == ["Alice"]


def test_the_last_departure_closes_the_room_for_every_tab(room_app: RoomApp) -> None:
    alice = room_app.register("Alice")
    _create(room_app, alice)

    with room_app.client.websocket_connect(SOCKET, headers=alice) as first_tab, room_app.client.websocket_connect(SOCKET, headers=alice) as second_tab:
        first_tab.receive_json()
        room_app.client.post("/api/rooms/current/leave", headers=alice)

        for tab in (first_tab, second_tab):
            assert _until(tab, lambda message: message["type"] in {"room.closed", "room.left"})["type"] == "room.closed"
            assert _closed_with(tab) == CLOSE_LEFT_ROOM


def test_resync_sends_the_full_state_again(room_app: RoomApp) -> None:
    alice = room_app.register("Alice")
    created = _create(room_app, alice)

    with room_app.client.websocket_connect(SOCKET, headers=alice) as socket:
        socket.receive_json()
        socket.send_json({"type": "resync"})
        resynced = _until(socket, lambda message: message["type"] == "room.snapshot")
        assert resynced["room"]["id"] == created["id"] and resynced["room"]["version"] == created["version"]


def test_a_chatty_client_is_cut_off(room_app: RoomApp) -> None:
    alice = room_app.register("Alice")
    _create(room_app, alice)

    with room_app.client.websocket_connect(SOCKET, headers=alice) as socket:
        socket.receive_json()
        for _ in range(11):
            socket.send_text('{"type":"pong"}')
        assert _closed_with(socket) == CLOSE_TOO_CHATTY


def test_an_oversized_message_is_cut_off(room_app: RoomApp) -> None:
    alice = room_app.register("Alice")
    _create(room_app, alice)

    with room_app.client.websocket_connect(SOCKET, headers=alice) as socket:
        socket.receive_json()
        socket.send_text("x" * 300)
        assert _closed_with(socket) == CLOSE_TOO_CHATTY


def test_a_failure_during_the_handshake_leaves_no_ghost_connection(room_app: RoomApp, monkeypatch: pytest.MonkeyPatch) -> None:
    alice = room_app.register("Alice")
    room_id = _create(room_app, alice)["id"]
    broadcaster = room_app.client.app.dependency_overrides[room_broadcaster]()  # type: ignore[attr-defined]
    original = broadcaster.broadcast

    async def unavailable(room_id: str, events: Any = ()) -> None:
        raise ConnectionError("base indisponible")

    monkeypatch.setattr(broadcaster, "broadcast", unavailable)
    with pytest.raises(ConnectionError):
        with room_app.client.websocket_connect(SOCKET, headers=alice) as socket:
            socket.receive_json()
            socket.receive_json()

    assert room_app.hub.connections(room_id) == [] and room_app.hub.online(room_id) == frozenset()
    monkeypatch.setattr(broadcaster, "broadcast", original)
    with room_app.client.websocket_connect(SOCKET, headers=alice) as socket:  # la reconnexion repart d'un hub propre
        assert _online(socket.receive_json()) == {"Alice": True}
