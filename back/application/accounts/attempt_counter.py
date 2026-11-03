from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

from exceptions import TooManyAttemptsError


@dataclass(frozen=True, slots=True)
class AttemptWindow:
    count: int
    resets_at_ms: int


class AttemptCounter(ABC):
    """Compteurs d'essais par fenêtre fixe, persistés : ils survivent à un redémarrage et sont partagés entre processus."""

    @abstractmethod
    async def peek(self, key: str, now_ms: int, window_ms: int) -> AttemptWindow: ...

    @abstractmethod
    async def hit(self, key: str, now_ms: int, window_ms: int) -> AttemptWindow:
        """Compte un essai de façon atomique et renvoie la fenêtre qui l'inclut."""

    @abstractmethod
    async def reset(self, key: str) -> None: ...

    @abstractmethod
    async def purge(self, started_before_ms: int) -> None: ...


@dataclass(frozen=True, slots=True)
class AttemptLimit:
    """Au plus `limit` essais par `window_ms` pour un même sujet (adresse IP, pseudo…) dans une portée donnée."""

    scope: str
    limit: int
    window_ms: int

    def key(self, subject: str) -> str:
        # Empreinte : la base ne stocke ni adresse IP ni pseudo en clair.
        return hashlib.sha256(f"{self.scope}:{subject}".encode("utf-8")).hexdigest()

    async def ensure_allowed(self, counter: AttemptCounter, subject: str, now_ms: int) -> None:
        self._raise_if_over(await counter.peek(self.key(subject), now_ms, self.window_ms), now_ms, self.limit - 1)

    async def count_attempt(self, counter: AttemptCounter, subject: str, now_ms: int) -> None:
        """Compte puis vérifie en une seule opération atomique : deux requêtes simultanées ne passent pas la limite."""
        self._raise_if_over(await counter.hit(self.key(subject), now_ms, self.window_ms), now_ms, self.limit)

    async def record(self, counter: AttemptCounter, subject: str, now_ms: int) -> None:
        await counter.hit(self.key(subject), now_ms, self.window_ms)

    async def reset(self, counter: AttemptCounter, subject: str) -> None:
        await counter.reset(self.key(subject))

    @staticmethod
    def _raise_if_over(window: AttemptWindow, now_ms: int, allowed: int) -> None:
        if window.count > allowed:
            raise TooManyAttemptsError(retry_after_seconds=max(1, -(-(window.resets_at_ms - now_ms) // 1000)))
