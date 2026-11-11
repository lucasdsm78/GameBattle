from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any, Optional

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from domain.rooms.models.room import Room
from domain.rooms.models.room_member import RoomMember
from domain.rooms.repositories.room_repository import RoomRepository
from exceptions import ConcurrentModificationError
from infrastructure.database.rooms.room_member_model import RoomMemberModel
from infrastructure.database.rooms.room_model import RoomModel

ROOMS, MEMBERS = RoomModel.__table__, RoomMemberModel.__table__


def _member(row: Any) -> RoomMember:
    return RoomMember(account_id=row.account_id, pseudo=row.pseudo, team=row.team, joined_at_ms=row.joined_at_ms)


def _room(row: Any, members: list[RoomMember]) -> Room:
    return Room(
        id=row.id,
        code=row.code,
        visibility=row.visibility,
        format=row.format,
        teams=tuple(row.teams),
        max_players=row.max_players,
        host_account_id=row.host_account_id,
        members=tuple(sorted(members, key=lambda member: member.joined_at_ms)),
        created_at_ms=row.created_at_ms,
        updated_at_ms=row.updated_at_ms,
        status=row.status,
        version=row.version,
    )


def _member_values(room_id: str, member: RoomMember) -> dict[str, Any]:
    return {"room_id": room_id, "account_id": member.account_id, "pseudo": member.pseudo, "team": member.team, "joined_at_ms": member.joined_at_ms}


class PostgreSQLRoomRepository(RoomRepository):
    """Salons et membres dans la transaction de l'unité de travail.

    Requêtes en lignes (pas d'objets ORM en cache de session) : ce qui est lu reflète toujours la base, même
    après une écriture dans la même transaction. `save` et `delete` ne passent qu'à la version lue.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, room_id: str) -> Optional[Room]:
        return await self._one(ROOMS.c.id == room_id)

    async def get_by_code(self, code: str) -> Optional[Room]:
        return await self._one(ROOMS.c.code == code)

    async def find_by_member(self, account_id: str) -> Optional[Room]:
        room_id = await self._session.scalar(select(MEMBERS.c.room_id).where(MEMBERS.c.account_id == account_id))
        return await self.get(room_id) if room_id else None

    async def list_open_public(self, limit: int) -> list[Room]:
        return await self._many(
            (ROOMS.c.visibility == "public") & (ROOMS.c.status == "lobby"), order_by=ROOMS.c.created_at_ms.desc(), limit=limit
        )

    async def list_inactive(self, updated_before_ms: int, limit: int) -> list[Room]:
        return await self._many((ROOMS.c.status == "lobby") & (ROOMS.c.updated_at_ms < updated_before_ms), order_by=ROOMS.c.updated_at_ms, limit=limit)

    async def add(self, room: Room) -> Room:
        try:
            await self._session.execute(
                insert(ROOMS).values(
                    id=room.id,
                    code=room.code,
                    visibility=room.visibility,
                    format=room.format,
                    teams=list(room.teams),
                    max_players=room.max_players,
                    host_account_id=room.host_account_id,
                    status=room.status,
                    version=1,
                    created_at_ms=room.created_at_ms,
                    updated_at_ms=room.updated_at_ms,
                )
            )
            if room.members:
                await self._session.execute(insert(MEMBERS), [_member_values(room.id, member) for member in room.members])
        except IntegrityError as exc:  # code déjà pris, ou joueur entré dans un autre salon entre-temps
            raise ConcurrentModificationError() from exc
        return replace(room, version=1)

    async def save(self, room: Room) -> Room:
        result = await self._session.execute(
            update(ROOMS)
            .where(ROOMS.c.id == room.id, ROOMS.c.version == room.version)
            .values(host_account_id=room.host_account_id, status=room.status, updated_at_ms=room.updated_at_ms, version=room.version + 1)
        )
        if result.rowcount != 1:
            raise ConcurrentModificationError()
        await self._sync_members(room)
        return replace(room, version=room.version + 1)

    async def delete(self, room: Room) -> None:
        # Membres d'abord : SQLite n'applique pas les ON DELETE CASCADE sans pragma.
        await self._session.execute(delete(MEMBERS).where(MEMBERS.c.room_id == room.id))
        result = await self._session.execute(delete(ROOMS).where(ROOMS.c.id == room.id, ROOMS.c.version == room.version))
        if result.rowcount != 1:
            raise ConcurrentModificationError()

    async def _sync_members(self, room: Room) -> None:
        stored = {row.account_id: row.team for row in (await self._session.execute(select(MEMBERS).where(MEMBERS.c.room_id == room.id))).all()}
        wanted = {member.account_id: member for member in room.members}
        try:
            if gone := set(stored) - set(wanted):
                await self._session.execute(delete(MEMBERS).where(MEMBERS.c.room_id == room.id, MEMBERS.c.account_id.in_(gone)))
            if arrivals := [_member_values(room.id, member) for account_id, member in wanted.items() if account_id not in stored]:
                await self._session.execute(insert(MEMBERS), arrivals)
            for account_id, member in wanted.items():
                if account_id in stored and stored[account_id] != member.team:
                    await self._session.execute(
                        update(MEMBERS).where(MEMBERS.c.room_id == room.id, MEMBERS.c.account_id == account_id).values(team=member.team)
                    )
        except IntegrityError as exc:  # le joueur vient d'entrer dans un autre salon
            raise ConcurrentModificationError() from exc

    async def _one(self, condition: ColumnElement[bool]) -> Optional[Room]:
        rooms = await self._many(condition, limit=1)
        return rooms[0] if rooms else None

    async def _many(self, condition: ColumnElement[bool], *, order_by: Any = None, limit: int) -> list[Room]:
        query = select(ROOMS).where(condition).limit(limit)
        rows = (await self._session.execute(query.order_by(order_by) if order_by is not None else query)).all()
        if not rows:
            return []
        members: dict[str, list[RoomMember]] = defaultdict(list)
        for row in (await self._session.execute(select(MEMBERS).where(MEMBERS.c.room_id.in_([row.id for row in rows])))).all():
            members[row.room_id].append(_member(row))
        return [_room(row, members[row.id]) for row in rows]
