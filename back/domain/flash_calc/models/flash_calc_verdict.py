from __future__ import annotations

from dataclasses import dataclass

from domain.shared.models.buzz_verdict import BuzzVerdict


@dataclass(frozen=True, slots=True)
class FlashCalcVerdict(BuzzVerdict):
    expression: str
    shown_result: int
    true_result: int
