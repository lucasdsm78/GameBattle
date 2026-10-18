from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, ClassVar, Self

TIE_LABEL = "Égalité"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def zero_scores(teams: list[str]) -> dict[str, int]:
    return {team: 0 for team in teams}


def pick_round_winner(teams: list[str], scores: dict[str, int]) -> str:
    """Équipe au meilleur score, ou `TIE_LABEL` si plusieurs équipes sont à égalité en tête."""
    best = max((scores.get(team, 0) for team in teams), default=0)
    leaders = [team for team in teams if scores.get(team, 0) == best]
    return leaders[0] if len(leaders) == 1 else TIE_LABEL


class GameState:
    """État d'un jeu, manipulé comme un objet-valeur : chaque transition renvoie un nouvel état.

    Renvoyer `self` signifie « aucun changement » : l'agrégat ne persiste ni ne diffuse rien.
    Un `winner_team` renseigné clôt la manche.
    """

    __slots__ = ()

    game_key: ClassVar[str]
    label: ClassVar[str]
    private_fields: ClassVar[frozenset[str]] = frozenset()

    winner_team: str | None

    @classmethod
    def for_new_manche(cls, teams: list[str], round_id: str) -> Self:
        return cls()

    def validate(self, teams: list[str]) -> None:
        raise NotImplementedError

    def expire_due(self, teams: list[str], now_ms: int) -> Self:
        return self

    def payload_extras(self, teams: list[str]) -> dict[str, Any]:
        return {}

    def to_payload(self, teams: list[str]) -> dict[str, Any]:
        return {**asdict(self), **self.payload_extras(teams)}  # type: ignore[call-overload]

    @classmethod
    def shared_view(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Vue envoyée à tous les clients : sans les champs internes au serveur."""
        if not cls.private_fields:
            return payload
        return {key: value for key, value in payload.items() if key not in cls.private_fields}

    @staticmethod
    def display_view(payload: dict[str, Any]) -> dict[str, Any]:
        """Vue de l'écran public : masque ce que les équipes ne doivent pas voir. Ne mute jamais `payload`."""
        return payload
