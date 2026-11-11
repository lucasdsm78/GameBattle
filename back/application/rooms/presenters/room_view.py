from __future__ import annotations

from collections.abc import Collection
from typing import Any

from application.rooms.presenters.room_host import host_pseudo
from domain.rooms.models.room import PLAYERS_PER_TEAM, Room
from domain.rooms.models.room_member import RoomMember

INVITE_PATH = "/join/{code}"


def _players(room: Room, viewer_id: str, online: Collection[str]) -> list[dict[str, Any]]:
    def view(member: RoomMember) -> dict[str, Any]:
        return {
            "pseudo": member.pseudo,
            "team": member.team,
            "is_host": member.account_id == room.host_account_id,
            "is_me": member.account_id == viewer_id,
            "online": member.account_id in online,
        }

    return [view(member) for member in sorted(room.members, key=lambda member: member.joined_at_ms)]


def room_view(room: Room, viewer_id: str, online: Collection[str] = ()) -> dict[str, Any]:
    """Le salon vu par l'un de ses membres : la seule vue qui porte le lien d'invitation. Aucun identifiant de compte."""
    me = room.member(viewer_id)
    return {
        "id": room.id,
        "visibility": room.visibility,
        "format": room.format,
        "status": room.status,
        "invite_path": INVITE_PATH.format(code=room.code),
        "host": host_pseudo(room),
        "player_count": len(room.members),
        "capacity": room.capacity,
        "teams": [{"name": team, "capacity": PLAYERS_PER_TEAM} for team in room.teams],
        "players": _players(room, viewer_id, online),
        "can_choose_team": room.team_choice_allowed,
        "me": {"pseudo": me.pseudo, "team": me.team, "is_host": me.account_id == room.host_account_id} if me else None,
        "version": room.version,
    }
