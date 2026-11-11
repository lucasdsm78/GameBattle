from __future__ import annotations

from typing import Any

from application.rooms.presenters.room_host import host_pseudo
from domain.rooms.models.room import PLAYERS_PER_TEAM, Room


def invitation_view(room: Room, viewer_id: str) -> dict[str, Any]:
    """Ce que montre un lien d'invitation avant d'entrer : de quoi choisir son équipe, sans le code ni l'identifiant du salon."""
    return {
        "visibility": room.visibility,
        "format": room.format,
        "status": room.status,
        "host": host_pseudo(room),
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
