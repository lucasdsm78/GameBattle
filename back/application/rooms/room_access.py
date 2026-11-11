from __future__ import annotations

from collections.abc import Awaitable
from typing import Optional

from application.rooms.room_unit_of_work import RoomUnitOfWork
from application.shared.attempt_limit import AttemptLimit, enforce
from domain.rooms.models.room import Room
from exceptions import RoomNotFoundError


async def reserve_attempts(uow: RoomUnitOfWork, now_ms: int, *limits: tuple[AttemptLimit, str]) -> None:
    """Compte l'essai dans sa propre transaction, puis refuse s'il dépasse la limite : un essai refusé compte aussi.

    Seule écriture permise aux lectures (aperçu d'invitation) : un compteur anti-énumération, jamais un salon.
    """
    reservations = [await limit.reserve(uow.attempts, subject, now_ms) for limit, subject in limits]
    await uow.commit()
    enforce(now_ms, *reservations)


async def require_open(lookup: Awaitable[Optional[Room]], missing: str) -> Room:
    """Le salon trouvé, s'il accepte encore du monde ; sinon une erreur « introuvable » (sans dire pourquoi)."""
    room = await lookup
    if room is None or room.status == "closed":
        raise RoomNotFoundError(missing)
    return room
