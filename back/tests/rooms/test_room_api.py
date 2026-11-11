from __future__ import annotations

from room_app_support import ORIGIN, RoomApp


def test_rooms_require_a_signed_in_player(room_app: RoomApp) -> None:
    client = room_app.client

    assert client.get("/api/rooms/current").status_code == 401
    assert client.post("/api/rooms", json={"visibility": "public", "format": "solo"}, headers={"Origin": ORIGIN}).status_code == 401


def test_writes_from_another_site_are_refused(room_app: RoomApp) -> None:
    alice = room_app.register("Alice") | {"Origin": "https://evil.example"}

    response = room_app.client.post("/api/rooms", json={"visibility": "public", "format": "solo"}, headers=alice)

    assert response.status_code == 403 and room_app.rooms.store.rooms == {}


def test_create_then_join_a_private_team_game_through_its_invitation(room_app: RoomApp) -> None:
    client = room_app.client
    alice, bob = room_app.register("Alice"), room_app.register("Bob")

    created = client.post("/api/rooms", json={"visibility": "private", "format": "teams", "team_count": 3}, headers=alice)
    assert created.status_code == 201, created.text
    invite = created.json()["invite_path"]
    code = invite.rsplit("/", 1)[1]
    assert client.get("/api/rooms/public", headers=bob).json() == {"rooms": []}  # privée : absente de la liste

    preview = client.get(f"/api/rooms/invitations/{code}", headers=bob).json()
    assert preview["can_choose_team"] and [team["name"] for team in preview["teams"]] == ["Rouges", "Bleus", "Verts"]

    joined = client.post(f"/api/rooms/invitations/{code}/join", json={"team": "Verts"}, headers=bob)
    assert joined.status_code == 200 and joined.json()["me"] == {"pseudo": "Bob", "team": "Verts", "is_host": False}
    assert client.post("/api/rooms/current/team", json={"team": "Rouges"}, headers=bob).json()["me"]["team"] == "Rouges"

    current = client.get("/api/rooms/current", headers=alice).json()["room"]
    assert [(player["pseudo"], player["team"], player["is_me"]) for player in current["players"]] == [
        ("Alice", "Rouges", True),
        ("Bob", "Rouges", False),
    ]
    assert client.post("/api/rooms/current/leave", headers=bob).status_code == 204
    assert client.get("/api/rooms/current", headers=bob).json() == {"room": None}


def test_join_a_public_game_from_the_list(room_app: RoomApp) -> None:
    client = room_app.client
    alice, bob, chloe = room_app.register("Alice"), room_app.register("Bob"), room_app.register("Chloe")
    room_id = client.post("/api/rooms", json={"visibility": "public", "format": "solo"}, headers=alice).json()["id"]

    listed = client.get("/api/rooms/public", headers=bob).json()["rooms"]
    assert [room["id"] for room in listed] == [room_id] and "invite_path" not in listed[0]

    assert client.post(f"/api/rooms/{room_id}/join", headers=bob).json()["player_count"] == 2
    full = client.post(f"/api/rooms/{room_id}/join", headers=chloe)
    assert full.status_code == 409 and full.json()["detail"] == "Ce salon est complet."


def test_room_errors_are_explicit(room_app: RoomApp) -> None:
    client = room_app.client
    alice, bob = room_app.register("Alice"), room_app.register("Bob")
    client.post("/api/rooms", json={"visibility": "public", "format": "solo"}, headers=alice)

    assert client.get("/api/rooms/invitations/ZZZZZZZZZZ", headers=bob).status_code == 404
    assert client.get("/api/rooms/invitations/not-a-code", headers=bob).status_code == 422
    assert client.post("/api/rooms/not-a-uuid/join", headers=bob).status_code == 422
    assert client.post("/api/rooms", json={"visibility": "public", "format": "solo"}, headers=alice).status_code == 409
    assert client.post("/api/rooms/current/leave", headers=bob).status_code == 404
    malformed = client.post("/api/rooms", json={"visibility": "secret", "format": "teams", "team_count": 9}, headers=bob)
    assert malformed.status_code == 422
