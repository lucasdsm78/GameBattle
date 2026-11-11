from __future__ import annotations

from pydantic import Field

from application.golden_family.commands.family_turn import FamilyTurnCommand


class FamilyAnswerCommand(FamilyTurnCommand):
    answer_index: int = Field(ge=0, le=9)
