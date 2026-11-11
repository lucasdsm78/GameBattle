from __future__ import annotations

from typing import Literal

from pydantic import Field

from application.shared.commands.input_model import InputModel
from domain.rooms.models.room import MAX_TEAMS, MIN_TEAMS


class CreateRoomCommand(InputModel):
    visibility: Literal["public", "private"]
    format: Literal["solo", "teams"]
    team_count: int = Field(default=MIN_TEAMS, ge=MIN_TEAMS, le=MAX_TEAMS)
