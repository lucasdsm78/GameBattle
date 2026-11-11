from __future__ import annotations

from collections.abc import Awaitable
from typing import Optional

from domain.rooms.models.room import Room
from exceptions import RoomNotFoundError


async def require_open(lookup: Awaitable[Optional[Room]], missing: str) -> Room:
    """Le salon trouvé, s'il accepte encore du monde ; sinon une erreur « introuvable » (sans dire pourquoi)."""
    room = await lookup
    if room is None or room.status == "closed":
        raise RoomNotFoundError(missing)
    return room
