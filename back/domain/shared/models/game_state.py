from __future__ import annotations

from dataclasses import asdict
from typing import Any, ClassVar, Self

from domain.shared.events.domain_event import DomainEvent


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

    def events_since(self, previous: Self, teams: list[str]) -> list[DomainEvent]:
        """Faits métier produits par la transition `previous` → `self`."""
        return []

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
