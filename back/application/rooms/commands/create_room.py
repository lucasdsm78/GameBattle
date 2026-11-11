from __future__ import annotations

from typing import Literal

from pydantic import Field

from application.shared.commands.input_model import InputModel
from domain.rooms.constants.room_limits import MAX_TEAMS, MIN_TEAMS, SOLO_MAX_PLAYERS, SOLO_MIN_PLAYERS


class CreateRoomCommand(InputModel):
    """`team_count` ne compte qu'en équipes, `max_players` qu'en solo (chacun pour soi)."""

    # Valeurs de `RoomVisibility` et `RoomFormat` (vérifié par les tests) : un Literal reste strict en JSON.
    visibility: Literal["public", "private"]
    format: Literal["solo", "teams"]
    team_count: int = Field(default=MIN_TEAMS, ge=MIN_TEAMS, le=MAX_TEAMS)
    max_players: int = Field(default=4, ge=SOLO_MIN_PLAYERS, le=SOLO_MAX_PLAYERS)
