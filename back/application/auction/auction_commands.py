from __future__ import annotations

from pydantic import Field

from application.shared.commands import InputModel, TeamName


class AuctionBidCommand(InputModel):
    team: TeamName
    target_count: int = Field(ge=1, le=100)
