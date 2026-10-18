from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Optional, Self

from application.shared.unit_of_work import UnitOfWork
from domain.game_night.models.game_config import GameConfig
from domain.game_night.repositories.game_config_repository import GameConfigRepository
from domain.shared.events.domain_event import DomainEvent


class GameConfigUnitOfWork(UnitOfWork):
    """Unité de travail mono-processus : un verrou asyncio sérialise les transactions.

    L'agrégat tient en une ligne : `repository.save` est déjà atomique, l'unité de travail garantit
    l'exclusivité, l'annulation de ce qui n'est pas validé et la remise des événements après l'écriture.
    """

    def __init__(self, repository: GameConfigRepository) -> None:
        self.game_configs = repository
        self._staged: Optional[GameConfig] = None
        self._lock: Optional[asyncio.Lock] = None
        self._lock_loop: Optional[asyncio.AbstractEventLoop] = None

    def _current_lock(self) -> asyncio.Lock:
        # Recréé si la boucle change (une boucle par `TestClient` dans les tests).
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock, self._lock_loop = asyncio.Lock(), loop
        return self._lock

    async def __aenter__(self) -> Self:
        await self._current_lock().acquire()
        self._staged = None
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None:
        self.rollback()
        self._current_lock().release()

    def add(self, config: GameConfig) -> None:
        self._staged = config

    async def commit(self) -> tuple[GameConfig, tuple[DomainEvent, ...]]:
        if self._staged is None:
            raise RuntimeError("Aucun état à valider dans cette unité de travail.")
        config, events = self._staged.pull_events()
        saved = await self.game_configs.save(config)
        self._staged = None
        return saved, events

    def rollback(self) -> None:
        self._staged = None
