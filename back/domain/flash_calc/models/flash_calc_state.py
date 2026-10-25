from __future__ import annotations

from dataclasses import dataclass, replace
from typing import ClassVar, Optional

from domain.flash_calc.events import CalculationShown, FlashCalcLevelReached
from domain.flash_calc.models.flash_calc_verdict import FlashCalcVerdict
from domain.flash_calc.services.flash_calc_generator import (
    display_ms_for,
    generate_calculation,
    level_for,
)
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.buzz_stream_state import BuzzStreamState
from exceptions import InvalidGameConfigError


@dataclass(slots=True)
class FlashCalcState(BuzzStreamState):
    """Des calculs défilent, de plus en plus vite : on buzze seulement s'ils sont justes."""

    game_key: ClassVar[str] = "flash_calc"
    label: ClassVar[str] = "Calcul flash"

    calc_number: int = 0
    expression: str = ""
    shown_result: int = 0
    true_result: int = 0
    verdict: Optional[FlashCalcVerdict] = None

    @property
    def level(self) -> int:
        return level_for(self.calc_number)

    def _validate_item(self, teams: list[str]) -> None:
        if self.calc_number < 1 or not self.expression or self.shown_result < 0 or self.true_result < 0:
            raise InvalidGameConfigError("Le calcul affiché est invalide.")

    def _show_next(self, now_ms: int) -> FlashCalcState:
        number = self.calc_number + 1
        level = level_for(number)
        calculation = generate_calculation(level, avoid=self.expression)
        return replace(
            self,
            calc_number=number,
            expression=calculation.expression,
            shown_result=calculation.shown_result,
            true_result=calculation.true_result,
            **self._running(now_ms, display_ms_for(level)),
        )

    def _is_buzz_correct(self) -> bool:
        return self.shown_result == self.true_result

    def _verdict_for(self, team: str, correct: bool, points: int) -> FlashCalcVerdict:
        return FlashCalcVerdict(
            team=team,
            correct=correct,
            points=points,
            expression=self.expression,
            shown_result=self.shown_result,
            true_result=self.true_result,
        )

    def events_since(self, previous: FlashCalcState, teams: list[str]) -> list[DomainEvent]:
        events = BuzzStreamState.events_since(self, previous, teams)
        if self.calc_number > previous.calc_number:
            if previous.calc_number and self.level > previous.level:
                events.append(FlashCalcLevelReached(self.level))
            events.append(CalculationShown(self.calc_number, self.level))
        return events
