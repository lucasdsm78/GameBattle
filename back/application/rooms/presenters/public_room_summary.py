from __future__ import annotations

from typing import Any

from application.rooms.presenters.room_host import host_pseudo
from domain.rooms.models.room import Room


def public_room_summary(room: Room) -> dict[str, Any]:
    """Une ligne de la liste des parties publiques, visible de tous : ni code d'invitation, ni liste de joueurs."""
    return {
        "id": room.id,
        "host": host_pseudo(room),
        "format": room.format,
        "team_count": len(room.teams),
        "player_count": len(room.members),
        "capacity": room.capacity,
    }
