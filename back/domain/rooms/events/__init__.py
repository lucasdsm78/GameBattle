"""Événements des salons : publics, ils ne portent que des pseudos, jamais d'identifiant de compte."""

from domain.rooms.events.host_changed import HostChanged
from domain.rooms.events.player_joined import PlayerJoined
from domain.rooms.events.player_left import PlayerLeft
from domain.rooms.events.room_closed import RoomClosed
from domain.rooms.events.room_opened import RoomOpened
from domain.rooms.events.team_changed import TeamChanged

__all__ = ["HostChanged", "PlayerJoined", "PlayerLeft", "RoomClosed", "RoomOpened", "TeamChanged"]
