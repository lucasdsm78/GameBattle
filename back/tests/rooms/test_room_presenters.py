from __future__ import annotations

import json

from room_support import ALICE, BOB, CHLOE

from application.rooms.presenters.invitation_view import invitation_view
from application.rooms.presenters.public_room_summary import public_room_summary
from application.rooms.presenters.room_view import room_view
from domain.rooms.models.room import Room

CODE = "ABCDEFGHJK"


def _room() -> Room:
    room = Room.open(
        room_id="5f0c1c8e-1111-4111-8111-111111111111", code=CODE, visibility="private", format="teams",
        team_count=2, host_account_id=ALICE.account_id, host_pseudo=ALICE.pseudo, now_ms=1,
    )
    return room.join(BOB.account_id, BOB.pseudo, 2, team="Bleus")


def _text(view: dict) -> str:
    return json.dumps(view, ensure_ascii=False)


def test_no_view_ever_exposes_an_account_id() -> None:
    room = _room()
    for view in (room_view(room, BOB.account_id), public_room_summary(room), invitation_view(room, CHLOE.account_id)):
        assert ALICE.account_id not in _text(view) and BOB.account_id not in _text(view)


def test_only_members_see_the_invitation_code() -> None:
    room = _room()

    assert room_view(room, BOB.account_id)["invite_path"] == f"/join/{CODE}"
    assert CODE not in _text(public_room_summary(room))  # liste publique : visible de tous
    assert CODE not in _text(invitation_view(room, CHLOE.account_id))  # celui qui a le lien n'a pas à le relire
    assert room.id not in _text(invitation_view(room, CHLOE.account_id))  # un salon privé ne se rejoint pas par son id


def test_the_public_summary_does_not_list_players() -> None:
    summary = public_room_summary(_room())

    assert set(summary) == {"id", "host", "format", "team_count", "player_count", "capacity"}
    assert "Bob" not in _text(summary) and summary["host"] == "Alice"


def test_each_member_sees_themselves() -> None:
    room = _room()

    assert room_view(room, BOB.account_id)["me"] == {"pseudo": "Bob", "team": "Bleus", "is_host": False}
    assert [player["is_me"] for player in room_view(room, ALICE.account_id)["players"]] == [True, False]
    assert invitation_view(room, BOB.account_id)["already_member"] and not invitation_view(room, CHLOE.account_id)["already_member"]
