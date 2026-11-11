from __future__ import annotations

import secrets
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from application.rooms.commands.change_team import ChangeTeamCommand
from application.rooms.commands.create_room import CreateRoomCommand
from application.rooms.commands.join_room import JoinRoomCommand
from application.rooms.presenters.invitation_view import invitation_view
from application.rooms.presenters.public_room_summary import public_room_summary
from application.rooms.presenters.room_view import room_view
from application.rooms.room_limits import RoomLimits
from application.rooms.room_unit_of_work import RoomUnitOfWork
from application.shared.attempt_limit import AttemptLimit, enforce
from application.shared.command_usecase import wall_clock_ms
from application.shared.outbox import NullOutboxNotifier, OutboxNotifier
from application.shared.player_identity import PlayerIdentity
from domain.rooms.models.room import Room
from exceptions import AlreadyInRoomError, ConcurrentModificationError, NotInRoomError, RoomNotFoundError

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O ni 1/I : lisible à voix haute
CODE_LENGTH = 10  # 32^10 ≈ 10^15 codes : introuvable par essais, d'autant que les essais sont limités
MUTATION_ATTEMPTS = 3  # reprises après un conflit d'écriture (deux joueurs qui entrent en même temps)
PUBLIC_LIST_LIMIT = 30


def room_stream(room_id: str) -> str:
    return f"room:{room_id}"


def new_invitation_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


RoomLoader = Callable[[RoomUnitOfWork], Awaitable[Optional[Room]]]
RoomChange = Callable[[Room], Room]


class RoomUseCase:
    """Créer, trouver, rejoindre, quitter un salon.

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

    # --- Lecture ---

    async def current(self, player: PlayerIdentity) -> Optional[dict[str, Any]]:
        async with self._unit_of_work() as uow:
            room = await uow.rooms.find_by_member(player.account_id)
        return room_view(room, player.account_id) if room else None

    async def current_room(self, player: PlayerIdentity) -> Optional[Room]:
        async with self._unit_of_work() as uow:
            return await uow.rooms.find_by_member(player.account_id)

    async def get_room(self, room_id: str) -> Optional[Room]:
        async with self._unit_of_work() as uow:
            return await uow.rooms.get(room_id)

    async def list_public(self) -> list[dict[str, Any]]:
        async with self._unit_of_work() as uow:
            rooms = await uow.rooms.list_open_public(PUBLIC_LIST_LIMIT)
        return [public_room_summary(room) for room in rooms if not room.is_full]

    async def preview_invitation(self, player: PlayerIdentity, code: str, client_ip: str) -> dict[str, Any]:
        async with self._unit_of_work() as uow:
            await self._reserve(uow, (self._limits.invitation_lookups_per_ip, client_ip))
            room = await self._require_open(uow.rooms.get_by_code(code), "Ce lien d'invitation n'existe pas ou a expiré.")
        return invitation_view(room, player.account_id)

    # --- Écritures ---

    async def create(self, player: PlayerIdentity, command: CreateRoomCommand) -> dict[str, Any]:
        for _ in range(MUTATION_ATTEMPTS):
            now = self._clock()
            try:
                async with self._unit_of_work() as uow:
                    await self._reserve(uow, (self._limits.rooms_created_per_player, player.account_id))
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
            await self._reserve(uow, (self._limits.invitation_lookups_per_ip, client_ip))
            return await uow.rooms.get_by_code(code)

        return await self._join(player, by_code, command, missing="Ce lien d'invitation n'existe pas ou a expiré.")

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
            room = await self._require_open(load(uow), missing)
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

    async def _reserve(self, uow: RoomUnitOfWork, *limits: tuple[AttemptLimit, str]) -> None:
        now = self._clock()
        reservations = [await limit.reserve(uow.attempts, subject, now) for limit, subject in limits]
        await uow.commit()  # l'essai compte même si la demande est refusée ensuite
        enforce(now, *reservations)

    @staticmethod
    async def _require_open(lookup: Awaitable[Optional[Room]], missing: str) -> Room:
        room = await lookup
        if room is None or room.status == "closed":
            raise RoomNotFoundError(missing)
        return room
