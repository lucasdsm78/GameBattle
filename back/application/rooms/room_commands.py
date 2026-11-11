from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import Field, StringConstraints

from application.shared.commands import InputModel
from domain.rooms.models.room import MAX_TEAMS, MIN_TEAMS

TeamChoice = Annotated[str, StringConstraints(min_length=1, max_length=20)]


class CreateRoomCommand(InputModel):
    visibility: Literal["public", "private"]
    format: Literal["solo", "teams"]
    team_count: int = Field(default=MIN_TEAMS, ge=MIN_TEAMS, le=MAX_TEAMS)


class JoinRoomCommand(InputModel):
    """`team` n'est retenue que dans une partie privée en équipes ; ailleurs, l'équipe est attribuée."""

    team: Optional[TeamChoice] = None


class ChangeTeamCommand(InputModel):
    team: TeamChoice
