from __future__ import annotations

from dataclasses import dataclass

HIDDEN_ANSWER = "Réponse masquée"


@dataclass(slots=True)
class CultureQuestion:
    id: str
    question: str
    answer: str
    explanation: str
    difficulty: str
