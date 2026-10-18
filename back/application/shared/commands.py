from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

CultureDifficulty = Literal["toutes", "facile", "moyen", "difficile"]
TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=40)]
Slug = Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"^[a-z0-9_-]+$")]


class InputModel(BaseModel):
    """Entrée client : types stricts, champs inconnus refusés, espaces superflus retirés."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True, frozen=True)


class TeamCommand(InputModel):
    team: TeamName


class AnswerCommand(InputModel):
    is_correct: bool
