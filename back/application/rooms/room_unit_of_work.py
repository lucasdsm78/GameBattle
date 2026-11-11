from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from application.shared.attempt_counter import AttemptCounter
from application.shared.outbox import Outbox
from domain.rooms.repositories.room_repository import RoomRepository


class RoomUnitOfWork(ABC):
    """Une transaction sur les salons, leur outbox d'événements et les compteurs d'essais.

    Même contrat que les autres unités de travail : tout ce qui est fait dans `async with uow:` partage la
    transaction, `commit()` valide d'un bloc, sortir sans `commit()` annule. Une instance par opération.
    """

    rooms: RoomRepository
    outbox: Outbox
    attempts: AttemptCounter

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: TracebackType | None
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...
