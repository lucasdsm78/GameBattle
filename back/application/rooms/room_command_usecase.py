from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from application.rooms.commands.change_team import ChangeTeamCommand
from application.rooms.commands.create_room import CreateRoomCommand
from application.rooms.commands.join_room import JoinRoomCommand
from application.rooms.invitation_codes import INVITATION_MISSING, new_invitation_code
from application.rooms.presenters.room_view import room_view
from application.rooms.room_access import require_open, reserve_attempts
from application.rooms.room_limits import RoomLimits
from application.rooms.room_unit_of_work import RoomUnitOfWork
from application.shared.command_usecase import wall_clock_ms
from application.shared.outbox import NullOutboxNotifier, OutboxNotifier
from application.shared.player_identity import PlayerIdentity
from domain.rooms.models.room import Room
from exceptions import AlreadyInRoomError, ConcurrentModificationError, NotInRoomError

MUTATION_ATTEMPTS = 3  # reprises après un conflit d'écriture (deux joueurs qui entrent en même temps)


def room_stream(room_id: str) -> str:
    return f"room:{room_id}"


RoomLoader = Callable[[RoomUnitOfWork], Awaitable[Optional[Room]]]
RoomChange = Callable[[Room], Room]


class RoomCommandUseCase:
    """Créer, rejoindre, quitter un salon, changer d'équipe (les lectures sont dans `RoomQueryUseCase`).

    Chaque écriture : verrou optimiste sur le salon, événements dans l'outbox de la même transaction, relais
    prévenu après validation. Un conflit (deux joueurs qui entrent au même instant) est rejoué sur l'état frais.
    """

    def __init__(
        self,
        unit_of_work: Callable[[], RoomUnitOfWork],
        *,
        notifier: OutboxNotifier = NullOutboxNotifier(),
        limits: RoomLimits = RoomLimits(),
        clock: Callable[[], int] = wall_clock_ms,
        new_code: Callable[[], str] = new_invitation_code,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._notifier = notifier
        self._limits = limits
        self._clock = clock
        self._new_code = new_code

    async def create(self, player: PlayerIdentity, command: CreateRoomCommand) -> dict[str, Any]:
        for _ in range(MUTATION_ATTEMPTS):
            now = self._clock()
            try:
                async with self._unit_of_work() as uow:
                    await reserve_attempts(uow, now, (self._limits.rooms_created_per_player, player.account_id))
                    await self._ensure_free(uow, player)
                    room = Room.open(
                        room_id=str(uuid.uuid4()),
                        code=self._new_code(),
                        visibility=command.visibility,
                        format=command.format,
                        team_count=command.team_count,
                        host_account_id=player.account_id,
                        host_pseudo=player.pseudo,
                        now_ms=now,
                    )
                    saved = await self._write(uow, room, new=True)
            except ConcurrentModificationError:
                continue  # code déjà pris ou joueur entré ailleurs entre-temps : on rejoue
            return room_view(saved, player.account_id)
        raise ConcurrentModificationError()

    async def join_by_invitation(self, player: PlayerIdentity, code: str, command: JoinRoomCommand, client_ip: str) -> dict[str, Any]:
        async def by_code(uow: RoomUnitOfWork) -> Optional[Room]:
            await reserve_attempts(uow, self._clock(), (self._limits.invitation_lookups_per_ip, client_ip))
            return await uow.rooms.get_by_code(code)

        return await self._join(player, by_code, command, missing=INVITATION_MISSING)

    async def join_public(self, player: PlayerIdentity, room_id: str) -> dict[str, Any]:
        async def public_by_id(uow: RoomUnitOfWork) -> Optional[Room]:
            room = await uow.rooms.get(room_id)
            return room if room and room.visibility == "public" else None  # un salon privé ne se trouve que par son lien

        return await self._join(player, public_by_id, JoinRoomCommand(), missing="Cette partie n'est plus disponible.")

    async def change_team(self, player: PlayerIdentity, command: ChangeTeamCommand) -> dict[str, Any]:
        room = await self._mutate(
            self._membership(player), lambda room: room.change_team(player.account_id, command.team, self._clock())
        )
        return room_view(room, player.account_id)

    async def leave(self, player: PlayerIdentity) -> None:
        await self._mutate(self._membership(player), lambda room: room.leave(player.account_id, self._clock()))

    async def purge_inactive(self, limit: int = 100) -> int:
        """Ménage : un salon sans activité depuis longtemps est fermé, et ses membres prévenus."""
        async with self._unit_of_work() as uow:
            rooms = await uow.rooms.list_inactive(self._clock() - self._limits.inactive_after_ms, limit)
        closed = 0
        for stale in rooms:
            try:
                async with self._unit_of_work() as uow:
                    await self._write(uow, stale.close_for_inactivity(self._clock()))
                closed += 1
            except ConcurrentModificationError:
                continue  # il s'est passé quelque chose entre-temps : il n'est plus inactif
        return closed

    # --- Mécanique ---

    async def _join(self, player: PlayerIdentity, load: RoomLoader, command: JoinRoomCommand, *, missing: str) -> dict[str, Any]:
        async def checked(uow: RoomUnitOfWork) -> Optional[Room]:
            room = await require_open(load(uow), missing)
            current = await uow.rooms.find_by_member(player.account_id)
            if current is not None and current.id != room.id:
                raise AlreadyInRoomError("Tu es déjà dans un autre salon : quitte-le d'abord.")
            return room

        room = await self._mutate(checked, lambda room: room.join(player.account_id, player.pseudo, self._clock(), team=command.team))
        return room_view(room, player.account_id)

    def _membership(self, player: PlayerIdentity) -> RoomLoader:
        async def load(uow: RoomUnitOfWork) -> Optional[Room]:
            room = await uow.rooms.find_by_member(player.account_id)
            if room is None:
                raise NotInRoomError("Tu n'es dans aucun salon.")
            return room

        return load

    async def _mutate(self, load: RoomLoader, change: RoomChange) -> Room:
        """Lit, applique, écrit avec verrou optimiste ; en cas de conflit, rejoue sur l'état frais."""
        for _ in range(MUTATION_ATTEMPTS):
            try:
                async with self._unit_of_work() as uow:
                    room = await load(uow)
                    assert room is not None
                    updated = change(room)
                    if updated is room:
                        return room  # rien à faire (double clic, déjà dans l'équipe…)
                    return await self._write(uow, updated)
            except ConcurrentModificationError:
                continue
        raise ConcurrentModificationError()

    async def _write(self, uow: RoomUnitOfWork, room: Room, *, new: bool = False) -> Room:
        room, events = room.pull_events()
        if room.status == "closed":
            await uow.rooms.delete(room)
            saved = room
        else:
            saved = await (uow.rooms.add(room) if new else uow.rooms.save(room))
        await uow.outbox.append(room_stream(room.id), events)
        await uow.commit()
        self._notifier.notify()  # après validation seulement : le relais ne publie que ce qui existe
        return saved

    async def _ensure_free(self, uow: RoomUnitOfWork, player: PlayerIdentity) -> None:
        if await uow.rooms.find_by_member(player.account_id) is not None:
            raise AlreadyInRoomError("Tu es déjà dans un salon : quitte-le d'abord.")
