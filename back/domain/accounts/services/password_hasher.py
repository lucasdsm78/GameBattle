from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class PasswordHasher(ABC):
    """Port du hachage des mots de passe : lent par conception, donc asynchrone (jamais sur la boucle d'événements)."""

    @abstractmethod
    async def hash(self, password: str) -> str: ...

    @abstractmethod
    async def verify(self, password_hash: Optional[str], password: str) -> bool:
        """`None` (compte inconnu) prend le même temps et renvoie `False` : la durée ne révèle pas si le pseudo existe."""

    @abstractmethod
    def needs_rehash(self, password_hash: str) -> bool: ...
