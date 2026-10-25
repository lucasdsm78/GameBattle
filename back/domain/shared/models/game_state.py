from __future__ import annotations

from typing import ClassVar, Self

from domain.shared.events.domain_event import DomainEvent


class GameState:
    """État d'un jeu, manipulé comme un objet-valeur : chaque transition renvoie un nouvel état.

    Renvoyer `self` signifie « aucun changement » : l'agrégat ne persiste ni ne diffuse rien.
    Un `winner_team` renseigné clôt la manche.
    """

    __slots__ = ()

    game_key: ClassVar[str]
    label: ClassVar[str]

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
