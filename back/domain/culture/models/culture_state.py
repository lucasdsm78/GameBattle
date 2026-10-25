from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

from domain.culture.events import CultureAnswerRevealed, CultureTiebreakStarted
from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.culture_question import CultureQuestion
from domain.shared.models.game_state import GameState
from domain.shared.services.question_catalog import pick_one_culture_question
from domain.shared.services.scoring import TIE_LABEL, zero_scores
from exceptions import InvalidGameConfigError

CULTURE_QUESTIONS_PER_ROUND = 10
CULTURE_PHASES = frozenset({"idle", "selecting", "question", "finished"})
CULTURE_TIEBREAK_DIFFICULTY = "difficile"


@dataclass(slots=True)
class CultureState(GameState):
    game_key: ClassVar[str] = "culture"
    label: ClassVar[str] = "Culture générale"

    phase: str = "idle"
    current_index: int = 0
    total_questions: int = 0
    difficulty: str = "toutes"
    current_question: Optional[CultureQuestion] = None
    asked_questions: list[str] = field(default_factory=list)
    current_buzzer_team: Optional[str] = None
    answered: bool = False
    scores: dict[str, int] = field(default_factory=dict)
    # Équipes à égalité après la dernière question : elles seules jouent la question de départage.
    tiebreak_teams: list[str] = field(default_factory=list)
    winner_team: Optional[str] = None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> CultureState:
        # Les questions sont tirées à la demande, après le choix de difficulté du présentateur.
        return cls(total_questions=CULTURE_QUESTIONS_PER_ROUND, scores=zero_scores(teams))

    def validate(self, teams: list[str]) -> None:
        allowed_teams = set(teams)
        if set(self.scores) - allowed_teams:
            raise InvalidGameConfigError("Les scores de culture générale contiennent une équipe inconnue.")
        if self.current_buzzer_team and self.current_buzzer_team not in allowed_teams:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if self.winner_team and self.winner_team not in allowed_teams and self.winner_team != TIE_LABEL:
            raise InvalidGameConfigError("Le gagnant de culture générale est inconnu.")
        if self.phase not in CULTURE_PHASES:
            raise InvalidGameConfigError("La phase de culture générale est invalide.")
        if self.current_index < 0:
            raise InvalidGameConfigError("L'index de question est invalide.")
        if (
            len(set(self.tiebreak_teams)) != len(self.tiebreak_teams)
            or set(self.tiebreak_teams) - allowed_teams
            or len(self.tiebreak_teams) == 1
        ):
            raise InvalidGameConfigError("Les équipes du départage de culture générale sont invalides.")
        if self.tiebreak_teams and self.current_buzzer_team and self.current_buzzer_team not in self.tiebreak_teams:
            raise InvalidGameConfigError("Seules les équipes à égalité jouent la question de départage.")

    @property
    def in_tiebreak(self) -> bool:
        return bool(self.tiebreak_teams)

    @property
    def questions_remaining(self) -> int:
        return max(self.total_questions - self.current_index, 0)

    def start(self) -> CultureState:
        if self.phase != "idle":
            raise InvalidGameConfigError("La manche de culture générale a déjà commencé.")
        return replace(self, phase="selecting", current_index=1, current_question=None, current_buzzer_team=None, answered=False)

    def select_difficulty(self, difficulty: str, round_id: str) -> CultureState:
        if self.phase != "selecting":
            raise InvalidGameConfigError("Le choix de la difficulté n'est pas disponible pour le moment.")
        if self.in_tiebreak and difficulty != CULTURE_TIEBREAK_DIFFICULTY:
            raise InvalidGameConfigError("La question de départage est toujours difficile.")
        picked = pick_one_culture_question(difficulty, set(self.asked_questions))
        if picked is None:
            raise InvalidGameConfigError("Aucune question disponible pour cette difficulté.")
        question = CultureQuestion(
            id=f"culture-{round_id}-{self.current_index}",
            question=picked["question"],
            answer=picked["answer"],
            explanation=picked["explanation"],
            difficulty=picked["difficulty"],
        )
        return replace(
            self,
            phase="question",
            difficulty=question.difficulty,
            current_question=question,
            asked_questions=[*self.asked_questions, question.question],
            current_buzzer_team=None,
            answered=False,
        )

    def register_buzzer(self, team: str) -> CultureState:
        if self.phase != "question":
            raise InvalidGameConfigError("Aucune question n'est affichée pour buzzer.")
        if team not in self.scores:
            raise InvalidGameConfigError("L'équipe qui a buzzé est inconnue.")
        if self.in_tiebreak and team not in self.tiebreak_teams:
            raise InvalidGameConfigError("Seules les équipes à égalité peuvent buzzer sur la question de départage.")
        if self.current_buzzer_team is not None and not self.answered:
            raise InvalidGameConfigError("Un buzz est déjà en attente de validation.")
        if self.answered:
            raise InvalidGameConfigError("La question a déjà été validée, passe à la suivante.")
        return replace(self, current_buzzer_team=team)

    def answer(self, is_correct: bool) -> CultureState:
        if self.phase != "question":
            raise InvalidGameConfigError("Aucune question en cours pour valider une réponse.")
        if self.current_buzzer_team is None:
            raise InvalidGameConfigError("Aucune équipe n'a buzzé pour valider une réponse.")
        if self.answered:
            raise InvalidGameConfigError("La question a déjà été validée, passe à la suivante.")
        if not is_correct:
            return replace(self, current_buzzer_team=None)
        team = self.current_buzzer_team
        scored = replace(self, scores={**self.scores, team: self.scores.get(team, 0) + 1}, answered=True)
        # Départage : la première bonne réponse remporte la manche.
        return replace(scored, phase="finished", tiebreak_teams=[], winner_team=team) if self.in_tiebreak else scored

    def reveal_answer(self) -> CultureState:
        """Personne ne trouve : le présentateur révèle la réponse, sans point."""
        if self.phase != "question":
            raise InvalidGameConfigError("Aucune question en cours pour révéler la réponse.")
        if self.answered:
            raise InvalidGameConfigError("La réponse est déjà révélée.")
        return replace(self, answered=True, current_buzzer_team=None)

    def next_question(self) -> CultureState:
        if self.phase != "question":
            raise InvalidGameConfigError("Commence d'abord la manche de culture générale.")
        if not self.answered:
            raise InvalidGameConfigError("Valide une bonne réponse ou révèle la réponse avant de passer à la suite.")
        next_question = replace(
            self, phase="selecting", current_index=self.current_index + 1, current_question=None, current_buzzer_team=None, answered=False
        )
        if not self.in_tiebreak and self.current_index < self.total_questions:
            return next_question
        best = max(self.scores.get(team, 0) for team in self.scores)
        leaders = [team for team in (self.tiebreak_teams or list(self.scores)) if self.scores.get(team, 0) == best]
        if len(leaders) == 1:
            return replace(self, phase="finished", current_buzzer_team=None, tiebreak_teams=[], winner_team=leaders[0])
        return replace(next_question, tiebreak_teams=leaders)

    def events_since(self, previous: CultureState, teams: list[str]) -> list[DomainEvent]:
        if self.tiebreak_teams and not previous.tiebreak_teams:
            return [CultureTiebreakStarted(tuple(self.tiebreak_teams))]
        if previous.phase != "question" or self.phase not in {"question", "finished"}:
            return []
        if self.answered and not previous.answered and self.current_buzzer_team is None:
            return [CultureAnswerRevealed(self.current_index)]
        if self.current_buzzer_team and self.current_buzzer_team != previous.current_buzzer_team:
            return [BuzzerPressed("culture", self.current_buzzer_team)]
        if previous.current_buzzer_team and not previous.answered:
            if self.answered:
                return [AnswerJudged("culture", previous.current_buzzer_team, correct=True)]
            if self.current_buzzer_team is None:
                return [AnswerJudged("culture", previous.current_buzzer_team, correct=False)]
        return []
