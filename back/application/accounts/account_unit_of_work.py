from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from application.shared.attempt_counter import AttemptCounter
from domain.accounts.repositories.player_account_repository import (
    PlayerAccountRepository,
)
from domain.accounts.repositories.player_session_repository import (
    PlayerSessionRepository,
)


class AccountUnitOfWork(ABC):
    """Une transaction sur les comptes, leurs sessions et les compteurs d'essais.

    - Tout ce qui est fait dans `async with uow:` partage la même transaction.
    - `commit()` valide d'un bloc ; on peut continuer à lire ensuite (nouvelle transaction).
    - Sortir du bloc sans `commit()` (ou sur exception) annule tout ce qui n'a pas été validé.
    - Une instance par opération : le cas d'usage reçoit une fabrique, jamais une instance partagée.
    """

    accounts: PlayerAccountRepository
    sessions: PlayerSessionRepository
    attempts: AttemptCounter

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...
