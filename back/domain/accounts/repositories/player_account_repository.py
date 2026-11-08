from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.pseudo import Pseudo


class PlayerAccountRepository(ABC):
    @abstractmethod
    async def get(self, account_id: str) -> Optional[PlayerAccount]: ...

    @abstractmethod
    async def find_by_pseudo(self, pseudo: Pseudo) -> Optional[PlayerAccount]:
        """Recherche sans tenir compte de la casse (`Pseudo.key`)."""

    @abstractmethod
    async def add(self, account: PlayerAccount) -> None:
        """Lève `PseudoAlreadyTakenError` si le pseudo est déjà pris, même par une inscription simultanée."""

    @abstractmethod
    async def save_password_hash(self, account: PlayerAccount) -> None: ...
