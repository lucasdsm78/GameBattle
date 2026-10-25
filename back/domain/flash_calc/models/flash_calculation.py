from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FlashCalculation:
    expression: str
    shown_result: int
    true_result: int

    @property
    def is_correct(self) -> bool:
        return self.shown_result == self.true_result
