from __future__ import annotations

import asyncio

import pytest
from room_support import ALICE, BOB, CHLOE, IP, build_rooms, events_of

from application.rooms.commands.change_team import ChangeTeamCommand
from application.rooms.commands.create_room import CreateRoomCommand
from application.rooms.commands.join_room import JoinRoomCommand
from application.rooms.room_command_usecase import MUTATION_ATTEMPTS, room_stream
from exceptions import (
    AlreadyInRoomError,
    ConcurrentModificationError,
    NotInRoomError,
    RoomFullError,
    RoomNotFoundError,
    TooManyAttemptsError,
)

PRIVATE_TEAMS = CreateRoomCommand(visibility="private", format="teams", team_count=2)
PUBLIC_SOLO = CreateRoomCommand(visibility="public", format="solo")


def _code(view: dict) -> str:
    return view["invite_path"].rsplit("/", 1)[1]


def test_creating_a_room_seats_the_host_and_hands_out_an_invitation_link() -> None:
    rooms = build_rooms()

    view = asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS))

    assert view["invite_path"].startswith("/join/") and view["host"] == "Alice" and view["version"] == 1
    assert view["me"] == {"pseudo": "Alice", "team": "Rouges", "is_host": True}
    assert view["can_choose_team"] is True and [team["name"] for team in view["teams"]] == ["Rouges", "Bleus"]
    assert "account_id" not in str(view) and ALICE.account_id not in str(view)
    assert [event for event, _ in events_of(rooms.store)] == ["room.opened", "room.player_joined"]
    assert {event.stream for event in rooms.store.outbox} == {room_stream(view["id"])}
    assert rooms.notifier.calls == 1


def test_a_player_belongs_to_one_room_at_a_time() -> None:
    rooms = build_rooms()
    asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS))
    other = asyncio.run(rooms.commands.create(BOB, PUBLIC_SOLO))

    with pytest.raises(AlreadyInRoomError):
        asyncio.run(rooms.commands.create(ALICE, PUBLIC_SOLO))
    with pytest.raises(AlreadyInRoomError):
        asyncio.run(rooms.commands.join_public(ALICE, other["id"]))


def test_joining_by_invitation_lets_a_friend_pick_a_team_in_a_private_game() -> None:
    rooms = build_rooms()
    code = _code(asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS)))

    preview = asyncio.run(rooms.queries.preview_invitation(BOB, code, IP))
    assert preview["can_choose_team"] is True and preview["already_member"] is False
    assert [(team["name"], team["players"], team["is_full"]) for team in preview["teams"]] == [("Rouges", ["Alice"], False), ("Bleus", [], False)]

    view = asyncio.run(rooms.commands.join_by_invitation(BOB, code, JoinRoomCommand(team="Rouges"), IP))

    assert view["me"]["team"] == "Rouges" and view["player_count"] == 2
    assert asyncio.run(rooms.queries.preview_invitation(BOB, code, IP))["already_member"] is True


def test_joining_twice_is_harmless_and_writes_nothing() -> None:
    rooms = build_rooms()
    code = _code(asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS)))
    asyncio.run(rooms.commands.join_by_invitation(BOB, code, JoinRoomCommand(), IP))
    written = len(rooms.store.outbox)

    again = asyncio.run(rooms.commands.join_by_invitation(BOB, code, JoinRoomCommand(team="Bleus"), IP))

    assert again["player_count"] == 2 and len(rooms.store.outbox) == written


def test_public_games_are_listed_without_their_code_and_balance_teams() -> None:
    rooms = build_rooms()
    created = asyncio.run(rooms.commands.create(ALICE, CreateRoomCommand(visibility="public", format="teams", team_count=2)))
    asyncio.run(rooms.commands.create(CHLOE, PRIVATE_TEAMS))

    listed = asyncio.run(rooms.queries.list_public())

    assert listed == [{"id": created["id"], "host": "Alice", "format": "teams", "team_count": 2, "player_count": 1, "capacity": 8}]
    joined = asyncio.run(rooms.commands.join_public(BOB, created["id"]))
    assert joined["me"]["team"] == "Bleus" and joined["can_choose_team"] is False


def test_a_private_room_cannot_be_joined_by_its_id() -> None:
    rooms = build_rooms()
    private = asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS))

    with pytest.raises(RoomNotFoundError):
        asyncio.run(rooms.commands.join_public(BOB, private["id"]))


def test_full_rooms_disappear_from_the_public_list_and_refuse_newcomers() -> None:
    rooms = build_rooms()
    duel = asyncio.run(rooms.commands.create(ALICE, PUBLIC_SOLO))
    asyncio.run(rooms.commands.join_public(BOB, duel["id"]))

    assert asyncio.run(rooms.queries.list_public()) == []
    with pytest.raises(RoomFullError):
        asyncio.run(rooms.commands.join_public(CHLOE, duel["id"]))


def test_changing_team_and_leaving() -> None:
    rooms = build_rooms()
    code = _code(asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS)))
    asyncio.run(rooms.commands.join_by_invitation(BOB, code, JoinRoomCommand(), IP))

    moved = asyncio.run(rooms.commands.change_team(BOB, ChangeTeamCommand(team="Rouges")))
    assert moved["me"]["team"] == "Rouges"

    asyncio.run(rooms.commands.leave(ALICE))
    assert asyncio.run(rooms.queries.current(ALICE)) is None
    assert asyncio.run(rooms.queries.current(BOB))["host"] == "Bob"  # type: ignore[index]
    with pytest.raises(NotInRoomError):
        asyncio.run(rooms.commands.leave(ALICE))


def test_the_last_player_leaving_deletes_the_room_and_its_link() -> None:
    rooms = build_rooms()
    code = _code(asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS)))

    asyncio.run(rooms.commands.leave(ALICE))

    assert rooms.store.rooms == {} and events_of(rooms.store)[-1] == ("room.closed", {"reason": "empty"})
    with pytest.raises(RoomNotFoundError):
        asyncio.run(rooms.queries.preview_invitation(BOB, code, IP))


def test_a_write_conflict_is_replayed_on_fresh_state() -> None:
    rooms = build_rooms()
    code = _code(asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS)))
    rooms.conflicts[0] = MUTATION_ATTEMPTS - 1

    view = asyncio.run(rooms.commands.join_by_invitation(BOB, code, JoinRoomCommand(), IP))

    assert view["player_count"] == 2 and view["version"] == 2


def test_persistent_conflicts_give_up_without_partial_writes() -> None:
    rooms = build_rooms()
    code = _code(asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS)))
    written = len(rooms.store.outbox)
    rooms.conflicts[0] = MUTATION_ATTEMPTS

    with pytest.raises(ConcurrentModificationError):
        asyncio.run(rooms.commands.join_by_invitation(BOB, code, JoinRoomCommand(), IP))
    assert len(rooms.store.outbox) == written and asyncio.run(rooms.queries.current(BOB)) is None


def test_a_stale_version_is_refused_by_the_repository() -> None:
    rooms = build_rooms()
    view = asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS))
    stale = rooms.store.rooms[view["id"]]
    asyncio.run(rooms.commands.join_by_invitation(BOB, _code(view), JoinRoomCommand(), IP))

    async def save_stale() -> None:
        from room_support import InMemoryRoomUnitOfWork

        async with InMemoryRoomUnitOfWork(rooms.store, [0]) as uow:
            await uow.rooms.save(stale.join(CHLOE.account_id, CHLOE.pseudo, 0))

    with pytest.raises(ConcurrentModificationError):
        asyncio.run(save_stale())


def test_invitation_codes_cannot_be_guessed_by_brute_force() -> None:
    rooms = build_rooms()
    for _ in range(30):
        with pytest.raises(RoomNotFoundError):
            asyncio.run(rooms.queries.preview_invitation(BOB, "ZZZZZZZZZZ", IP))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(rooms.queries.preview_invitation(BOB, "ZZZZZZZZZZ", IP))
    with pytest.raises(TooManyAttemptsError):
        asyncio.run(rooms.commands.join_by_invitation(BOB, "ZZZZZZZZZZ", JoinRoomCommand(), IP))


def test_room_creation_is_rate_limited_per_player() -> None:
    rooms = build_rooms()
    for _ in range(10):
        asyncio.run(rooms.commands.create(ALICE, PUBLIC_SOLO))
        asyncio.run(rooms.commands.leave(ALICE))

    with pytest.raises(TooManyAttemptsError):
        asyncio.run(rooms.commands.create(ALICE, PUBLIC_SOLO))


def test_an_invitation_code_collision_draws_a_new_code() -> None:
    rooms = build_rooms(codes=["ABCDEFGHJK", "ABCDEFGHJK", "MNPQRSTUVW"])
    asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS))

    view = asyncio.run(rooms.commands.create(BOB, PRIVATE_TEAMS))

    assert view["invite_path"] == "/join/MNPQRSTUVW"


def test_inactive_rooms_are_closed_by_the_janitor() -> None:
    rooms = build_rooms()
    asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS))
    rooms.clock.now += 5 * 3_600_000
    asyncio.run(rooms.commands.create(BOB, PUBLIC_SOLO))
    rooms.clock.now += 2 * 3_600_000

    assert asyncio.run(rooms.commands.purge_inactive()) == 1
    assert asyncio.run(rooms.queries.current(ALICE)) is None and asyncio.run(rooms.queries.current(BOB)) is not None
    assert events_of(rooms.store)[-1] == ("room.closed", {"reason": "inactive"})


def test_queries_never_change_a_room_nor_publish_anything() -> None:
    rooms = build_rooms()
    view = asyncio.run(rooms.commands.create(ALICE, PRIVATE_TEAMS))
    before = (dict(rooms.store.rooms), list(rooms.store.outbox), rooms.notifier.calls)

    asyncio.run(rooms.queries.current(ALICE))
    asyncio.run(rooms.queries.current_room(BOB))
    asyncio.run(rooms.queries.get_room(view["id"]))
    asyncio.run(rooms.queries.list_public())
    asyncio.run(rooms.queries.preview_invitation(BOB, _code(view), IP))

    assert (dict(rooms.store.rooms), list(rooms.store.outbox), rooms.notifier.calls) == before
    assert any(key.startswith("room_code:") for key in rooms.store.attempts)  # seule trace : le compteur anti-énumération
