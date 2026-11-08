from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.accounts.models.player_session import PlayerSession
from domain.accounts.repositories.player_session_repository import (
    PlayerSessionRepository,
)
from infrastructure.database.models import PlayerSessionModel


class PostgreSQLPlayerSessionRepository(PlayerSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, player_session: PlayerSession) -> None:
        self._session.add(
            PlayerSessionModel(
                token_hash=player_session.token_hash,
                account_id=player_session.account_id,
                expires_at_ms=player_session.expires_at_ms,
            )
        )
        await self._session.flush()

    async def get(self, token_hash: str) -> Optional[PlayerSession]:
        row = await self._session.get(PlayerSessionModel, token_hash)
        return PlayerSession(row.token_hash, row.account_id, row.expires_at_ms) if row else None

    async def save_expiry(self, player_session: PlayerSession) -> None:
        await self._session.execute(
            update(PlayerSessionModel)
            .where(PlayerSessionModel.token_hash == player_session.token_hash)
            .values(expires_at_ms=player_session.expires_at_ms)
        )

    async def delete(self, token_hash: str) -> None:
        await self._session.execute(delete(PlayerSessionModel).where(PlayerSessionModel.token_hash == token_hash))

    async def delete_expired(self, now_ms: int) -> None:
        await self._session.execute(delete(PlayerSessionModel).where(PlayerSessionModel.expires_at_ms <= now_ms))
