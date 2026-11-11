from __future__ import annotations

import pytest
from room_support import ALICE, BOB, CHLOE

from domain.rooms.events import HostChanged, PlayerJoined, PlayerLeft, RoomClosed, RoomOpened, TeamChanged
from domain.rooms.models.room import PLAYERS_PER_TEAM, Room
from exceptions import RoomFullError, RoomRuleError

NOW = 1_000_000


def _open(visibility: str = "private", format: str = "teams", team_count: int = 2) -> Room:
    return Room.open(
        room_id="room-1",
        code="ABCDEFGHJK",
        visibility=visibility,
        format=format,
        team_count=team_count,
        host_account_id=ALICE.account_id,
        host_pseudo=ALICE.pseudo,
        now_ms=NOW,
    )


def _fill(room: Room, count: int, *, team: str | None = None) -> Room:
    for index in range(count):
        room = room.join(f"guest-{index}", f"Invité{index}", NOW + index + 1, team=team)
    return room


def test_opening_seats_the_host_and_announces_the_room() -> None:
    room, events = _open().pull_events()

    assert room.teams == ("Rouges", "Bleus") and room.capacity == 2 * PLAYERS_PER_TEAM
    assert [(m.pseudo, m.team) for m in room.members] == [("Alice", "Rouges")] and room.host_account_id == ALICE.account_id
    assert events == (RoomOpened(visibility="private", format="teams", host="Alice"), PlayerJoined(pseudo="Alice", team="Rouges"))
    assert room.pending_events == ()


@pytest.mark.parametrize(("format", "team_count"), [("teams", 1), ("teams", 5), ("duel", 2)])
def test_unknown_formats_and_team_counts_are_refused(format: str, team_count: int) -> None:
    with pytest.raises(RoomRuleError):
        _open(format=format, team_count=team_count)


def test_solo_is_a_one_versus_one_where_each_player_is_their_own_side() -> None:
    room = _open(format="solo").join(BOB.account_id, BOB.pseudo, NOW + 1)

    assert room.teams == () and room.capacity == 2 and room.is_full
    assert [m.team for m in room.members] == ["Alice", "Bob"]
    with pytest.raises(RoomFullError):
        room.join(CHLOE.account_id, CHLOE.pseudo, NOW + 2)


def test_private_team_games_let_the_newcomer_pick_a_team() -> None:
    room = _open().join(BOB.account_id, BOB.pseudo, NOW + 1, team="Rouges")

    assert room.member(BOB.account_id).team == "Rouges"  # type: ignore[union-attr]
    with pytest.raises(RoomRuleError):
        room.join(CHLOE.account_id, CHLOE.pseudo, NOW + 2, team="Violets")


def test_a_full_team_cannot_be_picked_but_the_other_one_can() -> None:
    room = _fill(_open(), PLAYERS_PER_TEAM - 1, team="Rouges")

    with pytest.raises(RoomFullError):
        room.join(BOB.account_id, BOB.pseudo, NOW + 10, team="Rouges")
    assert room.join(BOB.account_id, BOB.pseudo, NOW + 10, team="Bleus").member(BOB.account_id).team == "Bleus"  # type: ignore[union-attr]


def test_public_team_games_balance_teams_and_ignore_the_wish() -> None:
    room = _fill(_open(visibility="public", team_count=3), 5, team="Rouges")

    assert [room.team_size(team) for team in room.teams] == [2, 2, 2]
    with pytest.raises(RoomRuleError):
        room.change_team(ALICE.account_id, "Bleus", NOW + 10)


def test_joining_twice_changes_nothing() -> None:
    room = _open().join(BOB.account_id, BOB.pseudo, NOW + 1)

    assert room.join(BOB.account_id, BOB.pseudo, NOW + 2) is room


def test_a_full_room_refuses_newcomers() -> None:
    room = _fill(_open(), 2 * PLAYERS_PER_TEAM - 1)

    assert room.is_full
    with pytest.raises(RoomFullError):
        room.join(BOB.account_id, BOB.pseudo, NOW + 100)


def test_changing_team_in_a_private_game() -> None:
    room, _ = _open().join(BOB.account_id, BOB.pseudo, NOW + 1, team="Rouges").pull_events()

    moved = room.change_team(BOB.account_id, "Bleus", NOW + 2)

    assert moved.member(BOB.account_id).team == "Bleus"  # type: ignore[union-attr]
    assert moved.pending_events == (TeamChanged(pseudo="Bob", team="Bleus"),) and moved.updated_at_ms == NOW + 2
    assert moved.change_team(BOB.account_id, "Bleus", NOW + 3) is moved
    with pytest.raises(RoomRuleError):
        moved.change_team(CHLOE.account_id, "Rouges", NOW + 3)  # pas membre


def test_the_host_leaving_hands_over_to_the_longest_present_player() -> None:
    room, _ = _open().join(BOB.account_id, BOB.pseudo, NOW + 1).join(CHLOE.account_id, CHLOE.pseudo, NOW + 2).pull_events()

    after = room.leave(ALICE.account_id, NOW + 3)

    assert after.host_account_id == BOB.account_id and after.member(ALICE.account_id) is None
    assert after.pending_events == (PlayerLeft(pseudo="Alice"), HostChanged(host="Bob"))
    assert after.leave(ALICE.account_id, NOW + 4) is after


def test_the_last_player_leaving_closes_the_room() -> None:
    room, _ = _open().pull_events()

    closed = room.leave(ALICE.account_id, NOW + 1)

    assert closed.status == "closed" and closed.members == ()
    assert closed.pending_events == (PlayerLeft(pseudo="Alice"), RoomClosed(reason="empty"))
    with pytest.raises(RoomRuleError):
        closed.join(BOB.account_id, BOB.pseudo, NOW + 2)


def test_closing_for_inactivity_empties_the_room() -> None:
    closed = _open().join(BOB.account_id, BOB.pseudo, NOW + 1).close_for_inactivity(NOW + 2)

    assert closed.status == "closed" and closed.members == () and closed.pending_events[-1] == RoomClosed(reason="inactive")
