from __future__ import annotations

from domain.rooms.models.room import Room


def host_pseudo(room: Room) -> str:
    """Le pseudo de l'hôte : c'est ainsi que les joueurs le reconnaissent, jamais par son identifiant de compte."""
    host = room.member(room.host_account_id)
    return host.pseudo if host else ""
