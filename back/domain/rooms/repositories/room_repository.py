from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.rooms.models.room import Room


class RoomRepository(ABC):
    """Salons et leurs membres. `save` et `delete` appliquent le verrou optimiste sur `Room.version`."""

    @abstractmethod
    async def get(self, room_id: str) -> Optional[Room]: ...

    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[Room]: ...

    @abstractmethod
    async def find_by_member(self, account_id: str) -> Optional[Room]: ...

    @abstractmethod
    async def list_open_public(self, limit: int) -> list[Room]:
        """Salons publics en attente de joueurs, les plus récents d'abord."""

    @abstractmethod
    async def list_inactive(self, updated_before_ms: int, limit: int) -> list[Room]: ...

    @abstractmethod
    async def add(self, room: Room) -> Room:
        """Écrit un nouveau salon (version 1). Code déjà pris ou joueur déjà ailleurs : `ConcurrentModificationError`."""

    @abstractmethod
    async def save(self, room: Room) -> Room:
        """Écrit le salon si personne ne l'a modifié depuis sa lecture ; renvoie la nouvelle version."""

    @abstractmethod
    async def delete(self, room: Room) -> None: ...
