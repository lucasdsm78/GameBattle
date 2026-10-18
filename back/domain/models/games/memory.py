from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from typing import Any, ClassVar, Optional
from uuid import uuid4

from domain.models.games.base import GameState
from domain.models.games.culture import HIDDEN_ANSWER
from domain.services.catalogs.culture import pick_one_culture_question
from domain.vo.culture_question import CultureQuestion
from exceptions import InvalidGameConfigError

MEMORY_PHASES = frozenset({"idle", "question", "recitation", "finished"})
MEMORY_CHAIN_LENGTH = 8
MEMORY_RULES_VERSION = 2


def pick_memory_question(asked_questions: list[str]) -> CultureQuestion:
    payload = pick_one_culture_question("toutes", set(asked_questions))
    if payload is None:
        raise InvalidGameConfigError("Aucune question de culture générale n'est disponible.")
    return CultureQuestion(
        id=f"memory-{uuid4().hex[:12]}",
        question=payload["question"],
        answer=payload["answer"],
        explanation=payload.get("explanation", ""),
        difficulty=payload["difficulty"],
    )


@dataclass(slots=True)
class MemoryState(GameState):
    game_key: ClassVar[str] = "memory"
    label: ClassVar[str] = "Mémoire en chaîne"

    phase: str = "idle"
    current_team_index: int = 0
    qualified_team_indices: list[int] = field(default_factory=list)
    disqualified_teams: list[str] = field(default_factory=list)
    current_question: Optional[CultureQuestion] = None
    validated_answers: list[str] = field(default_factory=list)
    asked_questions: list[str] = field(default_factory=list)
    turn_number: int = 0
    winner_team: Optional[str] = None
    rules_version: int = MEMORY_RULES_VERSION

    def validate(self, teams: list[str]) -> None:
        allowed_teams = set(teams)
        if self.phase not in MEMORY_PHASES:
            raise InvalidGameConfigError("La phase de Mémoire en chaîne est invalide.")
        if self.current_team_index < 0 or (teams and self.current_team_index >= len(teams)):
            raise InvalidGameConfigError("L'équipe courante de Mémoire en chaîne est invalide.")
        if len(set(self.qualified_team_indices)) != len(self.qualified_team_indices) or any(
            index < 0 or index >= len(teams) for index in self.qualified_team_indices
        ):
            raise InvalidGameConfigError("Les équipes qualifiées de Mémoire en chaîne sont invalides.")
        if len(set(self.disqualified_teams)) != len(self.disqualified_teams) or set(self.disqualified_teams) - allowed_teams:
            raise InvalidGameConfigError("Une équipe disqualifiée de Mémoire en chaîne est inconnue.")
        if self.phase == "question" and (
            len(self.qualified_team_indices) < 2
            or self.current_team_index not in self.qualified_team_indices
            or self.current_question is None
            or not 1 <= self.turn_number <= MEMORY_CHAIN_LENGTH
            or len(self.validated_answers) != self.turn_number
        ):
            raise InvalidGameConfigError("Le tour de Mémoire en chaîne est invalide.")
        if self.phase == "recitation" and (
            len(self.qualified_team_indices) < 2
            or self.current_team_index not in self.qualified_team_indices
            or self.current_question is not None
            or self.turn_number != MEMORY_CHAIN_LENGTH
            or len(self.validated_answers) != MEMORY_CHAIN_LENGTH
        ):
            raise InvalidGameConfigError("La récitation de Mémoire en chaîne est invalide.")
        if self.phase == "finished" and (
            len(self.qualified_team_indices) != 1
            or not self.winner_team
            or self.winner_team != teams[self.qualified_team_indices[0]]
        ):
            raise InvalidGameConfigError("Le vainqueur de Mémoire en chaîne est invalide.")
        if self.winner_team and self.winner_team not in allowed_teams:
            raise InvalidGameConfigError("Le gagnant de Mémoire en chaîne est inconnu.")
        if any(not answer.strip() for answer in self.validated_answers) or self.turn_number < 0:
            raise InvalidGameConfigError("La chaîne de réponses de Mémoire en chaîne est invalide.")
        if self.rules_version != MEMORY_RULES_VERSION:
            raise InvalidGameConfigError("La version des règles de Mémoire en chaîne est invalide.")

    def payload_extras(self, teams: list[str]) -> dict[str, Any]:
        return {"sequence_length": len(self.validated_answers), "chain_length": MEMORY_CHAIN_LENGTH}

    @staticmethod
    def display_view(payload: dict[str, Any]) -> dict[str, Any]:
        view = {**payload, "validated_answers": []}
        question = payload.get("current_question")
        if isinstance(question, dict):
            view["current_question"] = {**question, "answer": HIDDEN_ANSWER, "explanation": ""}
        return view

    def _ask(self, question: CultureQuestion, **changes: Any) -> MemoryState:
        return replace(self, current_question=question, asked_questions=[*self.asked_questions, question.question], **changes)

    def _restart_chain(self, team_index: int, **changes: Any) -> MemoryState:
        question = pick_memory_question(self.asked_questions)
        return self._ask(
            question, phase="question", current_team_index=team_index, validated_answers=[question.answer], turn_number=1, **changes
        )

    def start(self, teams: list[str]) -> MemoryState:
        if self.phase != "idle":
            raise InvalidGameConfigError("Mémoire en chaîne a déjà démarré.")
        qualified = list(range(len(teams)))
        start_index = random.randrange(len(qualified))
        return MemoryState(qualified_team_indices=qualified)._restart_chain(start_index)

    def next_question(self) -> MemoryState:
        if self.phase != "question" or self.current_question is None:
            raise InvalidGameConfigError("Aucune question de Mémoire en chaîne n'est en cours.")
        if self.turn_number == MEMORY_CHAIN_LENGTH:
            return replace(self, phase="recitation", current_question=None)
        question = pick_memory_question(self.asked_questions)
        return self._ask(question, validated_answers=[*self.validated_answers, question.answer], turn_number=self.turn_number + 1)

    def validate_sequence(self) -> MemoryState:
        if self.phase != "recitation":
            raise InvalidGameConfigError("La séquence ne peut être validée qu'après les 8 questions.")
        position = self.qualified_team_indices.index(self.current_team_index)
        return self._restart_chain(self.qualified_team_indices[(position + 1) % len(self.qualified_team_indices)])

    def disqualify_team(self, teams: list[str]) -> MemoryState:
        if self.phase != "recitation":
            raise InvalidGameConfigError("Une équipe ne peut être disqualifiée qu'après les 8 questions.")
        qualified = [index for index in self.qualified_team_indices if index != self.current_team_index]
        disqualified = [*self.disqualified_teams, teams[self.current_team_index]]
        if len(qualified) == 1:
            return replace(
                self,
                phase="finished",
                current_team_index=qualified[0],
                qualified_team_indices=qualified,
                disqualified_teams=disqualified,
                current_question=None,
                winner_team=teams[qualified[0]],
            )
        next_index = next(
            index
            for offset in range(1, len(teams) + 1)
            if (index := (self.current_team_index + offset) % len(teams)) in qualified
        )
        return self._restart_chain(next_index, qualified_team_indices=qualified, disqualified_teams=disqualified)
