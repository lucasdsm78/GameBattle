from __future__ import annotations

from application.shared.commands import CultureDifficulty, InputModel


class CultureDifficultyCommand(InputModel):
    difficulty: CultureDifficulty
