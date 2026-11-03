from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from exceptions import TooManyAttemptsError


@dataclass(frozen=True, slots=True)
class AttemptWindow:
    count: int
    resets_at_ms: int


class AttemptCounter(ABC):
    """Compteurs d'essais par fenêtre fixe, persistés et partagés entre processus.

    Aucune lecture séparée : on ne peut que réserver un essai (compter et obtenir le total en une opération
    atomique), si bien que deux requêtes simultanées ne voient jamais le même total.
    L'adaptateur ne stocke jamais `subject` (adresse IP, pseudo) en clair.
    """

    @abstractmethod
    async def hit(self, scope: str, subject: str, now_ms: int, window_ms: int) -> AttemptWindow: ...

    @abstractmethod
    async def reset(self, scope: str, subject: str) -> None: ...

    @abstractmethod
    async def purge(self, started_before_ms: int) -> None: ...


@dataclass(frozen=True, slots=True)
class Reservation:
    limit: int
    window: AttemptWindow

    @property
    def exceeded(self) -> bool:
        return self.window.count > self.limit


@dataclass(frozen=True, slots=True)
class AttemptLimit:
    """Au plus `limit` essais par `window_ms` pour un même sujet (adresse IP, pseudo…) dans une portée donnée."""

    scope: str
    limit: int
    window_ms: int

    async def reserve(self, counter: AttemptCounter, subject: str, now_ms: int) -> Reservation:
        return Reservation(self.limit, await counter.hit(self.scope, subject, now_ms, self.window_ms))

    async def reset(self, counter: AttemptCounter, subject: str) -> None:
        await counter.reset(self.scope, subject)


def enforce(now_ms: int, *reservations: Reservation) -> None:
    """Refuse si une des réservations dépasse sa limite ; l'attente annoncée est celle de la plus longue."""
    exceeded = [reservation.window.resets_at_ms for reservation in reservations if reservation.exceeded]
    if exceeded:
        raise TooManyAttemptsError(retry_after_seconds=max(1, -(-(max(exceeded) - now_ms) // 1000)))
