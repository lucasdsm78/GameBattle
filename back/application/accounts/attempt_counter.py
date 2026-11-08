from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


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
