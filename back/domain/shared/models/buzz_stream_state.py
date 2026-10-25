from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional, Self

from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.buzz_verdict import BuzzVerdict
from domain.shared.models.game_state import GameState
from domain.shared.services.scoring import award_buzz, zero_scores
from exceptions import InvalidGameConfigError

BUZZ_STREAM_PHASES = frozenset({"idle", "running", "feedback", "paused", "finished"})
TIMED_PHASES = frozenset({"running", "feedback"})
BUZZ_STREAM_WINNING_SCORE = 5
BUZZ_STREAM_FEEDBACK_MS = 1_500
# Un buzz reçu juste après l'apparition d'un élément est un réflexe sur le précédent : on l'ignore.
BUZZ_STREAM_LOCK_MS = 250


@dataclass(slots=True)
class BuzzStreamState(GameState):
    """Base des jeux « buzze seulement si… » : des éléments défilent seuls et le serveur juge chaque buzz.

    Buzz juste : +1 ; buzz faux : −1, sans jamais descendre sous 0. Chaque buzz est suivi d'un retour
    (`feedback`), puis le défilement reprend. La première équipe à `winning_score` points gagne.
    Un jeu décrit seulement ce qui défile : `_show_next`, `_is_buzz_correct` et `_verdict_for`.
    """

    winning_score: ClassVar[int] = BUZZ_STREAM_WINNING_SCORE
    # Le jeu peut-il révéler la réponse sans buzz (personne n'a trouvé) ?
    reveals_without_buzz: ClassVar[bool] = False

    phase: str = "idle"
    shown_at_ms: int = 0
    deadline_ms: int = 0  # fin de l'élément affiché, ou du retour après un buzz
    verdict: Optional[BuzzVerdict] = None
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> Self:
        return cls(scores=zero_scores(teams))

    # --- Ce que chaque jeu décrit ---

    def _show_next(self, now_ms: int) -> Self:
        """Affiche l'élément suivant (au lancement, à la reprise, après un élément ou un retour)."""
        raise NotImplementedError

    def _is_buzz_correct(self) -> bool:
        raise NotImplementedError

    def _verdict_for(self, team: str, correct: bool, points: int) -> BuzzVerdict:
        raise NotImplementedError

    def _on_timeout(self, now_ms: int) -> Self:
        """L'élément affiché est passé sans buzz."""
        return self._show_next(now_ms)

    def _validate_item(self, teams: list[str]) -> None:
        """Invariants de l'élément affiché, une fois le défilement lancé."""

    # --- Mécanique commune ---

    def _running(self, now_ms: int, duration_ms: int) -> dict[str, Any]:
        return {"phase": "running", "shown_at_ms": now_ms, "deadline_ms": now_ms + duration_ms, "verdict": None}

    def _feedback(self, now_ms: int, verdict: Optional[BuzzVerdict] = None) -> Self:
        return replace(self, phase="feedback", deadline_ms=now_ms + BUZZ_STREAM_FEEDBACK_MS, verdict=verdict)

    def validate(self, teams: list[str]) -> None:
        allowed = set(teams)
        if self.phase not in BUZZ_STREAM_PHASES:
            raise InvalidGameConfigError(f"La phase de « {self.label} » est invalide.")
        if self.phase == "idle" and not self.scores:
            return
        if set(self.scores) != allowed or any(
            not isinstance(score, int) or not 0 <= score <= self.winning_score for score in self.scores.values()
        ):
            raise InvalidGameConfigError(f"Les scores de « {self.label} » sont invalides.")
        if (self.phase == "finished") != (self.winner_team is not None):
            raise InvalidGameConfigError(f"Le vainqueur de « {self.label} » est incohérent.")
        if self.winner_team and self.scores.get(self.winner_team) != self.winning_score:
            raise InvalidGameConfigError(f"Le vainqueur de « {self.label} » doit avoir {self.winning_score} points.")
        if self.phase == "idle":
            return
        self._validate_item(teams)
        if self.phase in TIMED_PHASES and self.deadline_ms <= self.shown_at_ms:
            raise InvalidGameConfigError(f"Le chrono de « {self.label} » est invalide.")
        verdict_required = self.phase == "finished" or (self.phase == "feedback" and not self.reveals_without_buzz)
        verdict_allowed = self.phase in {"feedback", "finished"}
        if (
            (verdict_required and self.verdict is None)
            or (not verdict_allowed and self.verdict is not None)
            or (self.verdict and self.verdict.team not in allowed)
        ):
            raise InvalidGameConfigError(f"Le dernier buzz de « {self.label} » est invalide.")

    def start(self, teams: list[str], now_ms: int) -> Self:
        if self.phase != "idle":
            raise InvalidGameConfigError("Le défilement a déjà commencé.")
        return replace(self, scores=dict(self.scores) or zero_scores(teams))._show_next(now_ms)

    def expire_due(self, teams: list[str], now_ms: int) -> Self:
        if self.phase not in TIMED_PHASES or now_ms < self.deadline_ms:
            return self
        return self._on_timeout(now_ms) if self.phase == "running" else self._show_next(now_ms)

    def register_buzzer(self, teams: list[str], team: str, now_ms: int) -> Self:
        if team not in teams:
            raise InvalidGameConfigError("L’équipe qui buzze est inconnue.")
        if self.phase not in TIMED_PHASES:
            raise InvalidGameConfigError("Le défilement est en pause." if self.phase == "paused" else "Le défilement n’est pas en cours.")
        if self.phase == "feedback" or now_ms < self.shown_at_ms + BUZZ_STREAM_LOCK_MS:
            return self
        if now_ms >= self.deadline_ms:
            return self._on_timeout(now_ms)  # trop tard : l'élément est déjà passé
        correct = self._is_buzz_correct()
        scores, points = award_buzz(self.scores, team, correct)
        winner = team if scores[team] >= self.winning_score else None
        judged = replace(self._feedback(now_ms, self._verdict_for(team, correct, points)), scores=scores, winner_team=winner)
        return replace(judged, phase="finished") if winner else judged

    def pause(self) -> Self:
        if self.phase not in TIMED_PHASES:
            raise InvalidGameConfigError("Le défilement n’est pas en cours.")
        return replace(self, phase="paused", deadline_ms=0, verdict=None)

    def resume(self, now_ms: int) -> Self:
        if self.phase != "paused":
            raise InvalidGameConfigError("Le défilement n’est pas en pause.")
        return self._show_next(now_ms)

    def events_since(self, previous: Self, teams: list[str]) -> list[DomainEvent]:
        if self.verdict is None or previous.phase != "running":
            return []
        return [
            BuzzerPressed(self.game_key, self.verdict.team),
            AnswerJudged(self.game_key, self.verdict.team, correct=self.verdict.correct),
        ]
