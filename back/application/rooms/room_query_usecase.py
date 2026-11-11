from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from application.rooms.invitation_codes import INVITATION_MISSING
from application.rooms.presenters.invitation_view import invitation_view
from application.rooms.presenters.public_room_summary import public_room_summary
from application.rooms.presenters.room_view import room_view
from application.rooms.room_access import require_open
from application.rooms.room_limits import RoomLimits
from application.rooms.room_unit_of_work import RoomUnitOfWork
from application.shared.attempt_limit import reserve_attempts
from application.shared.command_usecase import wall_clock_ms
from application.shared.player_identity import PlayerIdentity
from domain.rooms.models.room import Room

PUBLIC_LIST_LIMIT = 30


class RoomQueryUseCase:
    """Lectures des salons : aucun salon modifié, aucun événement publié, rien de validé hormis le compteur d'essais
    de l'aperçu d'invitation (un code se devine sinon par essais successifs)."""

    def __init__(
        self, unit_of_work: Callable[[], RoomUnitOfWork], *, limits: RoomLimits = RoomLimits(), clock: Callable[[], int] = wall_clock_ms
    ) -> None:
        self._unit_of_work = unit_of_work
        self._limits = limits
        self._clock = clock

    async def current(self, player: PlayerIdentity) -> Optional[dict[str, Any]]:
        room = await self.current_room(player)
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
            await reserve_attempts(uow, self._clock(), (self._limits.invitation_lookups_per_ip, client_ip))
            room = await require_open(uow.rooms.get_by_code(code), INVITATION_MISSING)
        return invitation_view(room, player.account_id)
