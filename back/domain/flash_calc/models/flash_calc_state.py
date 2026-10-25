from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional

from domain.flash_calc.events import CalculationShown, FlashCalcLevelReached
from domain.flash_calc.models.flash_calc_verdict import FlashCalcVerdict
from domain.flash_calc.services.flash_calc_generator import (
    CALCS_PER_LEVEL,
    MAX_LEVEL,
    display_ms_for,
    generate_calculation,
    level_for,
)
from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.scoring import zero_scores
from exceptions import InvalidGameConfigError

FLASH_CALC_PHASES = frozenset({"idle", "running", "feedback", "paused", "finished"})
FLASH_CALC_WINNING_SCORE = 10
FLASH_CALC_FEEDBACK_MS = 1_500
# Un buzz reçu juste après l'apparition d'un calcul est un réflexe sur le précédent : on l'ignore.
FLASH_CALC_BUZZ_LOCK_MS = 250
TIMED_PHASES = frozenset({"running", "feedback"})


@dataclass(slots=True)
class FlashCalcState(GameState):
    """Des calculs défilent : on buzze seulement s'ils sont justes (+1), sinon −1 (sans descendre sous 0)."""

    game_key: ClassVar[str] = "flash_calc"
    label: ClassVar[str] = "Calcul flash"
    private_fields: ClassVar[frozenset[str]] = frozenset({"true_result"})

    phase: str = "idle"
    calc_number: int = 0
    expression: str = ""
    shown_result: int = 0
    true_result: int = 0
    shown_at_ms: int = 0
    deadline_ms: int = 0  # fin du calcul affiché, ou du retour après un buzz
    verdict: Optional[FlashCalcVerdict] = None
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> FlashCalcState:
        return cls(scores=zero_scores(teams))

    @property
    def level(self) -> int:
        return level_for(self.calc_number)

    def validate(self, teams: list[str]) -> None:
        allowed = set(teams)
        if self.phase not in FLASH_CALC_PHASES:
            raise InvalidGameConfigError("La phase du Calcul flash est invalide.")
        if self.phase == "idle" and not self.scores:
            return
        if set(self.scores) != allowed or any(
            not isinstance(score, int) or not 0 <= score <= FLASH_CALC_WINNING_SCORE for score in self.scores.values()
        ):
            raise InvalidGameConfigError("Les scores du Calcul flash sont invalides.")
        if (self.phase == "finished") != (self.winner_team is not None):
            raise InvalidGameConfigError("Le vainqueur du Calcul flash est incohérent.")
        if self.winner_team and self.scores.get(self.winner_team) != FLASH_CALC_WINNING_SCORE:
            raise InvalidGameConfigError(f"Le vainqueur du Calcul flash doit avoir {FLASH_CALC_WINNING_SCORE} points.")
        if self.phase == "idle":
            return
        if self.calc_number < 1 or not self.expression or self.shown_result < 0 or self.true_result < 0:
            raise InvalidGameConfigError("Le calcul affiché est invalide.")
        if self.phase in TIMED_PHASES and self.deadline_ms <= self.shown_at_ms:
            raise InvalidGameConfigError("Le chrono du Calcul flash est invalide.")
        has_verdict = self.phase in {"feedback", "finished"}
        if has_verdict != (self.verdict is not None) or (self.verdict and self.verdict.team not in allowed):
            raise InvalidGameConfigError("Le dernier buzz du Calcul flash est invalide.")

    def payload_extras(self, teams: list[str]) -> dict[str, Any]:
        return {
            "level": self.level,
            "max_level": MAX_LEVEL,
            "calcs_per_level": CALCS_PER_LEVEL,
            "calc_duration_ms": display_ms_for(self.level),
            "feedback_ms": FLASH_CALC_FEEDBACK_MS,
            "winning_score": FLASH_CALC_WINNING_SCORE,
        }

    def _next_calculation(self, now_ms: int) -> FlashCalcState:
        number = self.calc_number + 1
        level = level_for(number)
        calculation = generate_calculation(level, avoid=self.expression)
        return replace(
            self,
            phase="running",
            calc_number=number,
            expression=calculation.expression,
            shown_result=calculation.shown_result,
            true_result=calculation.true_result,
            shown_at_ms=now_ms,
            deadline_ms=now_ms + display_ms_for(level),
            verdict=None,
        )

    def start(self, teams: list[str], now_ms: int) -> FlashCalcState:
        if self.phase != "idle":
            raise InvalidGameConfigError("Le défilement a déjà commencé.")
        return replace(self, scores=dict(self.scores) or zero_scores(teams))._next_calculation(now_ms)

    def expire_due(self, teams: list[str], now_ms: int) -> FlashCalcState:
        return self._next_calculation(now_ms) if self.phase in TIMED_PHASES and now_ms >= self.deadline_ms else self

    def register_buzzer(self, teams: list[str], team: str, now_ms: int) -> FlashCalcState:
        if team not in teams:
            raise InvalidGameConfigError("L’équipe qui buzze est inconnue.")
        if self.phase not in TIMED_PHASES:
            raise InvalidGameConfigError(
                "Le défilement est en pause." if self.phase == "paused" else "Le défilement des calculs n’est pas en cours."
            )
        if self.phase == "feedback" or now_ms < self.shown_at_ms + FLASH_CALC_BUZZ_LOCK_MS:
            return self
        if now_ms >= self.deadline_ms:
            return self._next_calculation(now_ms)  # trop tard : le calcul est déjà passé
        correct = self.shown_result == self.true_result
        previous_score = self.scores.get(team, 0)
        score = previous_score + 1 if correct else max(0, previous_score - 1)
        winner = team if score >= FLASH_CALC_WINNING_SCORE else None
        return replace(
            self,
            phase="finished" if winner else "feedback",
            scores={**self.scores, team: score},
            deadline_ms=now_ms + FLASH_CALC_FEEDBACK_MS,
            verdict=FlashCalcVerdict(
                team=team,
                correct=correct,
                expression=self.expression,
                shown_result=self.shown_result,
                true_result=self.true_result,
                points=score - previous_score,
            ),
            winner_team=winner,
        )

    def pause(self) -> FlashCalcState:
        if self.phase not in TIMED_PHASES:
            raise InvalidGameConfigError("Le défilement n’est pas en cours.")
        return replace(self, phase="paused", deadline_ms=0, verdict=None)

    def resume(self, now_ms: int) -> FlashCalcState:
        if self.phase != "paused":
            raise InvalidGameConfigError("Le défilement n’est pas en pause.")
        return self._next_calculation(now_ms)

    def events_since(self, previous: FlashCalcState, teams: list[str]) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        if self.verdict is not None and previous.phase == "running":
            events.append(BuzzerPressed(self.game_key, self.verdict.team))
            events.append(AnswerJudged(self.game_key, self.verdict.team, correct=self.verdict.correct))
        if self.calc_number > previous.calc_number:
            if previous.calc_number and self.level > previous.level:
                events.append(FlashCalcLevelReached(self.level))
            events.append(CalculationShown(self.calc_number, self.level))
        return events
