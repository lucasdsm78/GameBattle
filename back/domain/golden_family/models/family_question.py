from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FamilyAnswer:
    text: str
    points: int


@dataclass(frozen=True, slots=True)
class FamilyQuestion:
    id: str
    text: str
    answers: list[FamilyAnswer]  # de la plus citée à la moins citée


@dataclass(frozen=True, slots=True)
class BoardSlot:
    """Une case du tableau : retournée ou non, et par quelle équipe (aucune si révélée par le présentateur)."""

    revealed: bool = False
    found_by: str | None = None


@dataclass(frozen=True, slots=True)
class FamilyAttempt:
    team: str
    answer_index: int | None  # None : la réponse ne figure pas au tableau
