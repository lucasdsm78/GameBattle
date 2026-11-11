from __future__ import annotations

from collections.abc import Collection
from typing import Any

from domain.rooms.models.room import PLAYERS_PER_TEAM, Room
from domain.rooms.models.room_member import RoomMember

INVITE_PATH = "/rejoindre/{code}"

# Aucune vue ne laisse sortir un identifiant de compte : les joueurs se reconnaissent à leur pseudo.


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


def _host_pseudo(room: Room) -> str:
    host = room.member(room.host_account_id)
    return host.pseudo if host else ""


def room_view(room: Room, viewer_id: str, online: Collection[str] = ()) -> dict[str, Any]:
    """Le salon vu par l'un de ses membres : seul un membre connaît le lien d'invitation."""
    me = room.member(viewer_id)
    return {
        "id": room.id,
        "visibility": room.visibility,
        "format": room.format,
        "status": room.status,
        "invite_path": INVITE_PATH.format(code=room.code),
        "host": _host_pseudo(room),
        "player_count": len(room.members),
        "capacity": room.capacity,
        "teams": [{"name": team, "capacity": PLAYERS_PER_TEAM} for team in room.teams],
        "players": _players(room, viewer_id, online),
        "can_choose_team": room.team_choice_allowed,
        "me": {"pseudo": me.pseudo, "team": me.team, "is_host": me.account_id == room.host_account_id} if me else None,
        "version": room.version,
    }


def public_room_summary(room: Room) -> dict[str, Any]:
    """Une ligne de la liste des parties publiques : ni code, ni liste de joueurs."""
    return {
        "id": room.id,
        "host": _host_pseudo(room),
        "format": room.format,
        "team_count": len(room.teams),
        "player_count": len(room.members),
        "capacity": room.capacity,
    }


def invitation_view(room: Room, viewer_id: str) -> dict[str, Any]:
    """Ce que montre un lien d'invitation avant d'entrer : de quoi choisir son équipe en connaissance de cause."""
    return {
        "visibility": room.visibility,
        "format": room.format,
        "status": room.status,
        "host": _host_pseudo(room),
        "player_count": len(room.members),
        "capacity": room.capacity,
        "is_full": room.is_full,
        "can_choose_team": room.team_choice_allowed,
        "already_member": room.member(viewer_id) is not None,
        "teams": [
            {
                "name": team,
                "capacity": PLAYERS_PER_TEAM,
                "players": [member.pseudo for member in room.members if member.team == team],
                "is_full": not room.has_room_in(team),
            }
            for team in room.teams
        ],
    }
