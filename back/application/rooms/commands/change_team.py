from __future__ import annotations

from application.rooms.commands.fields import TeamChoice
from application.shared.commands.input_model import InputModel


class ChangeTeamCommand(InputModel):
    team: TeamChoice
