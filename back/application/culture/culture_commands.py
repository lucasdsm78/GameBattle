from __future__ import annotations

from application.shared.commands.fields import CultureDifficulty
from application.shared.commands.input_model import InputModel


class CultureDifficultyCommand(InputModel):
    difficulty: CultureDifficulty
