from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from domain.events import DomainEvent
from domain.models.game_config import GameConfig
from domain.repositories.game_config import GameConfigRepository


class UnitOfWork(ABC):
    """Transaction applicative sur l'agrégat de la soirée.

    - `async with uow:` ouvre une transaction exclusive : les commandes sont appliquées une par une.
    - `add(config)` prépare le nouvel état ; rien n'est écrit avant `commit()`.
    - `commit()` persiste l'agrégat sans ses événements, puis renvoie ceux-ci pour publication.
    - Sortir du bloc sans `commit()` (ou sur exception) annule tout ce qui avait été préparé.
    """

    game_configs: GameConfigRepository

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None: ...

    @abstractmethod
    def add(self, config: GameConfig) -> None: ...

    @abstractmethod
    async def commit(self) -> tuple[GameConfig, tuple[DomainEvent, ...]]: ...

    @abstractmethod
    def rollback(self) -> None: ...
