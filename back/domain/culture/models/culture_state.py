from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional

from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.events.domain_event import DomainEvent
from domain.shared.models.culture_question import HIDDEN_ANSWER, CultureQuestion
from domain.shared.models.game_state import GameState
from domain.shared.services.question_catalog import pick_one_culture_question
from domain.shared.services.scoring import TIE_LABEL, pick_round_winner, zero_scores
from exceptions import InvalidGameConfigError

CULTURE_QUESTIONS_PER_ROUND = 10
CULTURE_PHASES = frozenset({"idle", "selecting", "question", "finished"})


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

    @property
    def questions_remaining(self) -> int:
        return max(self.total_questions - self.current_index, 0)

    def payload_extras(self, teams: list[str]) -> dict[str, Any]:
        return {"questions_remaining": self.questions_remaining}

    @staticmethod
    def display_view(payload: dict[str, Any]) -> dict[str, Any]:
        question = payload.get("current_question")
        if not isinstance(question, dict):
            return payload
        hidden = {"explanation": ""} if payload.get("answered") else {"answer": HIDDEN_ANSWER, "explanation": ""}
        return {**payload, "current_question": {**question, **hidden}}

    def start(self) -> CultureState:
        if self.phase != "idle":
            raise InvalidGameConfigError("La manche de culture générale a déjà commencé.")
        return replace(self, phase="selecting", current_index=1, current_question=None, current_buzzer_team=None, answered=False)

    def select_difficulty(self, difficulty: str, round_id: str) -> CultureState:
        if self.phase != "selecting":
            raise InvalidGameConfigError("Le choix de la difficulté n'est pas disponible pour le moment.")
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
        return replace(self, scores={**self.scores, team: self.scores.get(team, 0) + 1}, answered=True)

    def next_question(self) -> CultureState:
        if self.phase != "question":
            raise InvalidGameConfigError("Commence d'abord la manche de culture générale.")
        if not self.answered:
            raise InvalidGameConfigError("Valide d'abord une bonne réponse avant de passer à la question suivante.")
        next_index = self.current_index + 1
        if next_index <= self.total_questions:
            return replace(
                self, phase="selecting", current_index=next_index, current_question=None, current_buzzer_team=None, answered=False
            )
        winner = pick_round_winner(list(self.scores), self.scores)
        return replace(self, phase="finished", current_buzzer_team=None, winner_team=winner)

    def events_since(self, previous: CultureState, teams: list[str]) -> list[DomainEvent]:
        if previous.phase != "question" or self.phase != "question":
            return []
        if self.current_buzzer_team and self.current_buzzer_team != previous.current_buzzer_team:
            return [BuzzerPressed("culture", self.current_buzzer_team)]
        if previous.current_buzzer_team and not previous.answered:
            if self.answered:
                return [AnswerJudged("culture", previous.current_buzzer_team, correct=True)]
            if self.current_buzzer_team is None:
                return [AnswerJudged("culture", previous.current_buzzer_team, correct=False)]
        return []
