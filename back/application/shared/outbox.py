from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Optional

from domain.shared.events.domain_event import DomainEvent


class Outbox(ABC):
    """Événements à publier, écrits dans la même transaction que l'agrégat qui les produit.

    Une écriture validée garantit leur publication (un relais les diffuse ensuite) ; une écriture annulée les
    emporte avec elle : jamais d'événement publié pour un état qui n'existe pas, ni d'état sans son événement.
    `audience` restreint un événement privé à un compte ; `None` : tous les abonnés du flux.
    """

    @abstractmethod
    async def append(self, stream: str, events: Sequence[DomainEvent], audience: Optional[str] = None) -> None: ...


class OutboxNotifier(ABC):
    """Prévient le relais qu'il y a du nouveau, pour publier sans attendre son prochain passage."""

    @abstractmethod
    def notify(self) -> None: ...


class NullOutboxNotifier(OutboxNotifier):
    def notify(self) -> None:
        return None
