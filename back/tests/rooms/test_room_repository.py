from __future__ import annotations

import asyncio

import pytest
from room_support import ALICE, BOB, CHLOE

from application.rooms.commands.change_team import ChangeTeamCommand
from application.rooms.commands.create_room import CreateRoomCommand
from application.rooms.commands.join_room import JoinRoomCommand
from application.rooms.room_usecase import RoomUseCase
from domain.rooms.models.room import Room
from exceptions import AlreadyInRoomError, ConcurrentModificationError
from infrastructure.database.database import Database
from infrastructure.database.outbox.outbox_store import OutboxStore
from infrastructure.repositories.rooms.room_unit_of_work import SqlRoomUnitOfWork

SECRET = b"secret-de-test-des-compteurs-0123456789"
IP = "203.0.113.7"


def _use_case(database: Database) -> RoomUseCase:
    return RoomUseCase(lambda: SqlRoomUnitOfWork(database, SECRET))


async def _stored(database: Database, room_id: str) -> Room | None:
    async with SqlRoomUnitOfWork(database, SECRET) as uow:
        return await uow.rooms.get(room_id)


def test_a_room_round_trips_with_its_members_in_arrival_order(sqlite_database: Database) -> None:
    rooms = _use_case(sqlite_database)

    async def scenario() -> None:
        view = await rooms.create(ALICE, CreateRoomCommand(visibility="private", format="teams", team_count=3))
        code = view["invite_path"].rsplit("/", 1)[1]
        await rooms.join_by_invitation(BOB, code, JoinRoomCommand(team="Verts"), IP)
        await rooms.join_by_invitation(CHLOE, code, JoinRoomCommand(), IP)
        await rooms.change_team(CHLOE, ChangeTeamCommand(team="Verts"))

        stored = await _stored(sqlite_database, view["id"])
        assert stored is not None and stored.code == code and stored.teams == ("Rouges", "Bleus", "Verts")
        assert [(m.pseudo, m.team) for m in stored.members] == [("Alice", "Rouges"), ("Bob", "Verts"), ("Chloé", "Verts")]
        assert stored.version == 4

        async with SqlRoomUnitOfWork(sqlite_database, SECRET) as uow:
            assert (await uow.rooms.get_by_code(code)) == stored
            assert (await uow.rooms.find_by_member(BOB.account_id)) == stored

    asyncio.run(scenario())


def test_a_stale_write_is_refused(sqlite_database: Database) -> None:
    rooms = _use_case(sqlite_database)

    async def scenario() -> None:
        view = await rooms.create(ALICE, CreateRoomCommand(visibility="public", format="teams"))
        stale = await _stored(sqlite_database, view["id"])
        assert stale is not None
        await rooms.join_public(BOB, view["id"])

        async with SqlRoomUnitOfWork(sqlite_database, SECRET) as uow:
            with pytest.raises(ConcurrentModificationError):
                await uow.rooms.save(stale.join(CHLOE.account_id, CHLOE.pseudo, 0))
        async with SqlRoomUnitOfWork(sqlite_database, SECRET) as uow:
            with pytest.raises(ConcurrentModificationError):
                await uow.rooms.delete(stale)

    asyncio.run(scenario())


def test_a_player_cannot_be_seated_in_two_rooms_even_in_a_race(sqlite_database: Database) -> None:
    rooms = _use_case(sqlite_database)

    async def scenario() -> None:
        first = await rooms.create(ALICE, CreateRoomCommand(visibility="public", format="solo"))
        second = await rooms.create(BOB, CreateRoomCommand(visibility="public", format="teams"))
        # La course : Chloé entre dans les deux salons « en même temps ». La base tranche (account_id unique).
        one, other = await _stored(sqlite_database, first["id"]), await _stored(sqlite_database, second["id"])
        assert one is not None and other is not None
        async with SqlRoomUnitOfWork(sqlite_database, SECRET) as uow:
            await uow.rooms.save(one.join(CHLOE.account_id, CHLOE.pseudo, 1))
            await uow.commit()
        async with SqlRoomUnitOfWork(sqlite_database, SECRET) as uow:
            with pytest.raises(ConcurrentModificationError):
                await uow.rooms.save(other.join(CHLOE.account_id, CHLOE.pseudo, 1))
        with pytest.raises(AlreadyInRoomError):
            await rooms.join_public(CHLOE, second["id"])

    asyncio.run(scenario())


def test_events_are_written_with_the_room_and_relayed_once(sqlite_database: Database) -> None:
    rooms, store = _use_case(sqlite_database), OutboxStore(sqlite_database)

    async def scenario() -> None:
        view = await rooms.create(ALICE, CreateRoomCommand(visibility="private", format="solo"))
        await rooms.leave(ALICE)

        pending = await store.pending(10)
        assert [(event.stream, event.event_type) for event in pending] == [
            (f"room:{view['id']}", "room.opened"),
            (f"room:{view['id']}", "room.player_joined"),
            (f"room:{view['id']}", "room.player_left"),
            (f"room:{view['id']}", "room.closed"),
        ]
        assert pending[1].payload == {"pseudo": "Alice", "team": "Alice"} and pending[1].audience is None
        assert await _stored(sqlite_database, view["id"]) is None  # salon vide : supprimé, membres compris

        await store.mark_published([event.id for event in pending[:2]], now_ms=1_000)
        assert [event.event_type for event in await store.pending(10)] == ["room.player_left", "room.closed"]
        await store.mark_published([event.id for event in pending[2:]], now_ms=5_000)
        await store.purge_published(published_before_ms=2_000)
        assert await store.pending(10) == []

    asyncio.run(scenario())


def test_a_rolled_back_write_leaves_no_event_behind(sqlite_database: Database) -> None:
    store = OutboxStore(sqlite_database)

    async def scenario() -> None:
        room = Room.open(
            room_id="00000000-0000-4000-8000-000000000000", code="ABCDEFGHJK", visibility="public", format="solo",
            team_count=2, host_account_id=ALICE.account_id, host_pseudo=ALICE.pseudo, now_ms=1,
        )
        async with SqlRoomUnitOfWork(sqlite_database, SECRET) as uow:
            room, events = room.pull_events()
            await uow.rooms.add(room)
            await uow.outbox.append("room:x", events)  # pas de commit : tout repart avec la transaction
        assert await store.pending(10) == [] and await _stored(sqlite_database, room.id) is None

    asyncio.run(scenario())


def test_the_janitor_query_only_sees_quiet_lobbies(sqlite_database: Database) -> None:
    clock = [1_000_000]
    rooms = RoomUseCase(lambda: SqlRoomUnitOfWork(sqlite_database, SECRET), clock=lambda: clock[0])

    async def scenario() -> None:
        await rooms.create(ALICE, CreateRoomCommand(visibility="public", format="solo"))
        clock[0] += 7 * 3_600_000
        await rooms.create(BOB, CreateRoomCommand(visibility="public", format="solo"))

        assert await rooms.purge_inactive() == 1
        assert await rooms.current(ALICE) is None and await rooms.current(BOB) is not None
        assert [summary["host"] for summary in await rooms.list_public()] == ["Bob"]

    asyncio.run(scenario())
