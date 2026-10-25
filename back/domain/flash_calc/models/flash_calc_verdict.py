from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FlashCalcVerdict:
    team: str
    correct: bool
    expression: str
    shown_result: int
    true_result: int
    points: int  # +1, -1, ou 0 quand l'équipe était déjà à 0
