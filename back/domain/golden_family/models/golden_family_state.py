from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.golden_family.events import (
    FamilyAnswerRevealed,
    FamilyBoardRevealed,
    FamilyControlTaken,
    FamilyQuestionShown,
    FamilyStrikeGiven,
)
from domain.golden_family.models.family_question import BoardSlot, FamilyAttempt, FamilyQuestion
from domain.golden_family.services.golden_family_catalog import (
    FAMILY_QUESTIONS_BY_ID,
    pick_family_question,
)
from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.game_state import GameState
from domain.shared.services.scoring import zero_scores
from exceptions import InvalidGameConfigError

GOLDEN_FAMILY_PHASES = frozenset({"idle", "faceoff", "duel", "control", "steal", "revealed", "finished"})
# duel : chaque équipe donne une réponse pour prendre la main ; control : l'équipe qui a la main enchaîne ;
# steal : après 3 fautes, les autres équipes tentent une réponse chacune.
ANSWERING_PHASES = frozenset({"duel", "control", "steal"})
QUESTION_PHASES = frozenset({"faceoff", *ANSWERING_PHASES})
GOLDEN_FAMILY_WINNING_SCORE = 300
GOLDEN_FAMILY_MAX_STRIKES = 3


def _others(teams: list[str], team: str) -> list[str]:
    """Les autres équipes, dans l'ordre de jeu qui suit `team`."""
    index = teams.index(team)
    return [*teams[index + 1 :], *teams[:index]]


@dataclass(slots=True)
class GoldenFamilyState(GameState):
    """Une famille en or : chaque bonne réponse rapporte ses points à l'équipe qui la trouve.

    Face-à-face : la première équipe à buzzer répond ; si c'est la réponse la plus citée, elle prend la
    main, sinon chaque équipe répond et la meilleure réponse prend la main. Après 3 fautes, les autres
    équipes répondent une fois chacune et la meilleure reprend la main ; si toutes échouent, la main
    revient à l'équipe fautive pour une réponse, et ainsi de suite jusqu'à une bonne réponse.
    """

    game_key: ClassVar[str] = "golden_family"
    label: ClassVar[str] = "Une famille en or"

    phase: str = "idle"
    question_number: int = 0
    question: Optional[FamilyQuestion] = None
    board: list[BoardSlot] = field(default_factory=list)
    current_team: Optional[str] = None  # l'équipe qui doit répondre maintenant
    control_team: Optional[str] = None  # l'équipe qui a la main
    steal_from: Optional[str] = None  # l'équipe qui a fait 3 fautes
    strikes: int = 0
    pending_teams: list[str] = field(default_factory=list)  # équipes qui répondront ensuite, une fois chacune
    attempts: list[FamilyAttempt] = field(default_factory=list)  # réponses du tour en cours (duel ou vol)
    # Compteurs monotones : `turn` rend les décisions du présentateur idempotentes, `misses` rythme les croix.
    turn: int = 0
    misses: int = 0
    used_questions: list[str] = field(default_factory=list)
    scores: dict[str, int] = field(default_factory=dict)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> GoldenFamilyState:
        return cls(scores=zero_scores(teams))

    # --- Invariants ---

    def validate(self, teams: list[str]) -> None:
        allowed = set(teams)
        if self.phase not in GOLDEN_FAMILY_PHASES:
            raise InvalidGameConfigError("La phase d’Une famille en or est invalide.")
        if self.phase == "idle" and not self.scores:
            return
        if set(self.scores) != allowed or any(not isinstance(score, int) or score < 0 for score in self.scores.values()):
            raise InvalidGameConfigError("Les scores d’Une famille en or sont invalides.")
        if (self.phase == "finished") != (self.winner_team is not None):
            raise InvalidGameConfigError("Le vainqueur d’Une famille en or est incohérent.")
        if self.winner_team and self.scores.get(self.winner_team, 0) < GOLDEN_FAMILY_WINNING_SCORE:
            raise InvalidGameConfigError(f"Le vainqueur d’Une famille en or doit avoir {GOLDEN_FAMILY_WINNING_SCORE} points.")
        if self.phase == "idle":
            return
        if self.question is None or FAMILY_QUESTIONS_BY_ID.get(self.question.id) != self.question:
            raise InvalidGameConfigError("La question d’Une famille en or est invalide.")
        if len(self.board) != len(self.question.answers) or any(
            (slot.found_by is not None and (slot.found_by not in allowed or not slot.revealed)) for slot in self.board
        ):
            raise InvalidGameConfigError("Le tableau d’Une famille en or est invalide.")
        if self.phase in {"revealed", "finished"} and not all(slot.revealed for slot in self.board):
            raise InvalidGameConfigError("Le tableau d’une question terminée doit être entièrement révélé.")
        named = [self.current_team, self.control_team, self.steal_from, *self.pending_teams, *(a.team for a in self.attempts)]
        if any(team is not None and team not in allowed for team in named):
            raise InvalidGameConfigError("Une équipe d’Une famille en or est inconnue.")
        if not 0 <= self.strikes <= GOLDEN_FAMILY_MAX_STRIKES or not 0 <= self.misses <= self.turn:
            raise InvalidGameConfigError("Les fautes d’Une famille en or sont invalides.")
        if len(set(self.pending_teams)) != len(self.pending_teams) or self.current_team in self.pending_teams:
            raise InvalidGameConfigError("L’ordre de passage d’Une famille en or est invalide.")
        if (self.phase in ANSWERING_PHASES) != (self.current_team is not None):
            raise InvalidGameConfigError("L’équipe qui répond est incohérente.")
        if self.phase == "control" and self.current_team != self.control_team:
            raise InvalidGameConfigError("Seule l’équipe qui a la main répond.")
        if self.phase == "steal" and self.steal_from is None:
            raise InvalidGameConfigError("Le vol de main d’Une famille en or est invalide.")
        if len(set(self.used_questions)) != len(self.used_questions) or self.question.id not in self.used_questions:
            raise InvalidGameConfigError("Une question d’Une famille en or a été tirée plusieurs fois.")

    # --- Actions ---

    def show_next_question(self, teams: list[str]) -> GoldenFamilyState:
        if self.phase not in {"idle", "revealed"}:
            raise InvalidGameConfigError("Une question est déjà en cours.")
        question, restarted = pick_family_question(self.used_questions)
        return replace(
            self,
            phase="faceoff",
            question_number=self.question_number + 1,
            question=question,
            board=[BoardSlot() for _ in question.answers],
            current_team=None,
            control_team=None,
            steal_from=None,
            strikes=0,
            pending_teams=[],
            attempts=[],
            used_questions=[*([] if restarted else self.used_questions), question.id],
            scores=dict(self.scores) or zero_scores(teams),
        )

    def register_buzzer(self, teams: list[str], team: str) -> GoldenFamilyState:
        if team not in teams:
            raise InvalidGameConfigError("L’équipe qui buzze est inconnue.")
        if self.phase != "faceoff":
            raise InvalidGameConfigError("Les buzzers ne sont pas ouverts pour le moment.")
        return replace(self, phase="duel", current_team=team, pending_teams=_others(teams, team), attempts=[])

    def give_answer(self, teams: list[str], answer_index: int, turn: int) -> GoldenFamilyState:
        """Le présentateur désigne la réponse du tableau que l'équipe vient de donner."""
        if turn != self.turn:
            return self  # décision déjà prise (double appui ou message rejoué)
        team = self._answering_team()
        assert self.question is not None
        if not 0 <= answer_index < len(self.question.answers):
            raise InvalidGameConfigError("Cette réponse ne fait pas partie du tableau.")
        if self.board[answer_index].revealed:
            raise InvalidGameConfigError("Cette réponse est déjà révélée.")
        board = list(self.board)
        board[answer_index] = BoardSlot(revealed=True, found_by=team)
        scores = {**self.scores, team: self.scores.get(team, 0) + self.question.answers[answer_index].points}
        answered = replace(self, board=board, scores=scores, turn=self.turn + 1)
        if scores[team] >= GOLDEN_FAMILY_WINNING_SCORE:
            return answered._close("finished", winner=team)
        if all(slot.revealed for slot in board):
            return answered._close("revealed")
        return answered if self.phase == "control" else answered._after_attempt(teams, FamilyAttempt(team, answer_index))

    def strike(self, teams: list[str], turn: int) -> GoldenFamilyState:
        """FAUTE : la réponse donnée ne figure pas au tableau."""
        if turn != self.turn:
            return self
        team = self._answering_team()
        missed = replace(self, turn=self.turn + 1, misses=self.misses + 1)
        if self.phase != "control":
            return missed._after_attempt(teams, FamilyAttempt(team, None))
        strikes = self.strikes + 1
        if strikes < GOLDEN_FAMILY_MAX_STRIKES:
            return replace(missed, strikes=strikes)
        others = _others(teams, team)
        return replace(
            missed, phase="steal", strikes=strikes, control_team=None, steal_from=team,
            current_team=others[0], pending_teams=others[1:], attempts=[],
        )

    def reveal_all(self) -> GoldenFamilyState:
        if self.phase not in QUESTION_PHASES:
            raise InvalidGameConfigError("Aucune question en cours.")
        return self._close("revealed")

    # --- Mécanique ---

    def _answering_team(self) -> str:
        if self.phase not in ANSWERING_PHASES or self.current_team is None:
            raise InvalidGameConfigError("Aucune équipe ne doit répondre pour le moment.")
        return self.current_team

    def _after_attempt(self, teams: list[str], attempt: FamilyAttempt) -> GoldenFamilyState:
        """Duel ou vol : la meilleure réponse du tour prend la main, une fois que chacun a répondu."""
        attempts = [*self.attempts, attempt]
        if self.phase == "duel" and not self.attempts and attempt.answer_index == 0:
            return self._give_control(attempt.team)  # le premier à buzzer a trouvé la réponse la plus citée
        if self.pending_teams:
            return replace(self, attempts=attempts, current_team=self.pending_teams[0], pending_teams=self.pending_teams[1:])
        best = self._best(attempts)
        if best is not None:
            return self._give_control(best)
        if self.phase == "duel":
            return replace(self, phase="faceoff", current_team=None, pending_teams=[], attempts=[])
        # Personne n'a trouvé : la main tourne entre l'équipe fautive et les autres jusqu'à une bonne réponse.
        assert self.steal_from is not None
        next_teams = [self.steal_from] if attempt.team != self.steal_from else _others(teams, self.steal_from)
        return replace(self, attempts=[], current_team=next_teams[0], pending_teams=next_teams[1:])

    def _best(self, attempts: list[FamilyAttempt]) -> Optional[str]:
        assert self.question is not None
        found = [(self.question.answers[a.answer_index].points, -order, a.team)
                 for order, a in enumerate(attempts) if a.answer_index is not None]
        return max(found)[2] if found else None

    def _give_control(self, team: str) -> GoldenFamilyState:
        return replace(
            self, phase="control", control_team=team, current_team=team, steal_from=None, strikes=0,
            pending_teams=[], attempts=[],
        )

    def _close(self, phase: str, winner: Optional[str] = None) -> GoldenFamilyState:
        board = [slot if slot.revealed else BoardSlot(revealed=True) for slot in self.board]
        return replace(
            self, phase=phase, board=board, current_team=None, pending_teams=[], attempts=[], winner_team=winner,
        )

    # --- Événements ---

    def events_since(self, previous: GoldenFamilyState, teams: list[str]) -> list[DomainEvent]:
        if self.question_number > previous.question_number:
            assert self.question is not None
            return [FamilyQuestionShown(self.question_number, len(self.question.answers))]
        events: list[DomainEvent] = []
        if previous.phase == "faceoff" and self.phase == "duel" and self.current_team:
            events.append(BuzzerPressed(self.game_key, self.current_team))
        if self.question is not None:
            for answer, before, after in zip(self.question.answers, previous.board, self.board):
                if after.found_by and not before.revealed:
                    events.append(AnswerJudged(self.game_key, after.found_by, correct=True))
                    events.append(FamilyAnswerRevealed(answer.text, answer.points, after.found_by))
        if self.misses > previous.misses and previous.current_team:
            events.append(AnswerJudged(self.game_key, previous.current_team, correct=False))
            if self.strikes > previous.strikes:
                events.append(FamilyStrikeGiven(previous.current_team, self.strikes))
        if self.control_team and self.control_team != previous.control_team:
            events.append(FamilyControlTaken(self.control_team))
        if self.phase in {"revealed", "finished"} and previous.phase in QUESTION_PHASES:
            events.append(FamilyBoardRevealed(self.question_number))
        return events
