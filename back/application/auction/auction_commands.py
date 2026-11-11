from __future__ import annotations

from pydantic import Field

from application.shared.commands.fields import TeamName
from application.shared.commands.input_model import InputModel


class AuctionBidCommand(InputModel):
    team: TeamName
    target_count: int = Field(ge=1, le=100)
