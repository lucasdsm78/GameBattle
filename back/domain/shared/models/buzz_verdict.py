from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BuzzVerdict:
    """Résultat d'un buzz jugé par le serveur, affiché le temps du retour."""

    team: str
    correct: bool
    points: int  # +1, -1, ou 0 quand l'équipe était déjà à 0
