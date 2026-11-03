from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.accounts.models.player_session import PlayerSession


class PlayerSessionRepository(ABC):
    @abstractmethod
    async def add(self, session: PlayerSession) -> None: ...

    @abstractmethod
    async def get(self, token_hash: str) -> Optional[PlayerSession]: ...

    @abstractmethod
    async def save_expiry(self, session: PlayerSession) -> None: ...

    @abstractmethod
    async def delete(self, token_hash: str) -> None: ...

    @abstractmethod
    async def delete_expired(self, now_ms: int) -> None: ...
