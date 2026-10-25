from __future__ import annotations

from pydantic import Field

from application.shared.commands import InputModel


class FamilyTurnCommand(InputModel):
    # Tour vu par le présentateur : un double appui ou un message rejoué est ignoré.
    turn: int = Field(ge=0, le=100_000)


class FamilyAnswerCommand(FamilyTurnCommand):
    answer_index: int = Field(ge=0, le=9)
