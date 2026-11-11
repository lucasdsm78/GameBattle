from __future__ import annotations

from application.shared.commands.fields import TeamName
from application.shared.commands.input_model import InputModel


class TeamCommand(InputModel):
    team: TeamName
