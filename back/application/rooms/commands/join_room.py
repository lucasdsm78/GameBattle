from __future__ import annotations

from typing import Optional

from application.rooms.commands.fields import TeamChoice
from application.shared.commands.input_model import InputModel


class JoinRoomCommand(InputModel):
    """`team` n'est retenue que dans une partie privée en équipes ; ailleurs, l'équipe est attribuée."""

    team: Optional[TeamChoice] = None
