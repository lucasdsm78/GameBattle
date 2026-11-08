from __future__ import annotations

import hashlib
import hmac

from sqlalchemy import case, delete
from sqlalchemy.ext.asyncio import AsyncSession

from application.accounts.attempt_counter import AttemptCounter, AttemptWindow
from infrastructure.database.models.accounts.auth_attempt_model import AuthAttemptModel
from infrastructure.database.upsert import upsert_insert


class SqlAttemptCounter(AttemptCounter):
    """Fenêtres fixes en base : un seul upsert `… RETURNING` par essai, atomique même sous concurrence.

    Les clés sont des HMAC-SHA256 à clé secrète dédiée : sans le secret, impossible de retrouver une adresse IP
    ou un pseudo par énumération (l'espace IPv4 et les pseudos sont trop petits pour un simple hachage).
    Changer le secret remet simplement les compteurs à zéro : ils ne vivent pas plus d'une heure.
    """

    def __init__(self, session: AsyncSession, secret: bytes) -> None:
        self._session = session
        self._secret = secret

    def _key(self, scope: str, subject: str) -> str:
        return hmac.new(self._secret, f"{scope}:{subject}".encode("utf-8"), hashlib.sha256).hexdigest()

    async def hit(self, scope: str, subject: str, now_ms: int, window_ms: int) -> AttemptWindow:
        insert = upsert_insert(self._session, AuthAttemptModel).values(
            key=self._key(scope, subject), window_start_ms=now_ms, count=1
        )
        expired = AuthAttemptModel.window_start_ms + window_ms <= insert.excluded.window_start_ms
        upsert = insert.on_conflict_do_update(
            index_elements=[AuthAttemptModel.key],
            set_={
                "count": case((expired, 1), else_=AuthAttemptModel.count + 1),
                "window_start_ms": case((expired, insert.excluded.window_start_ms), else_=AuthAttemptModel.window_start_ms),
            },
        ).returning(AuthAttemptModel.window_start_ms, AuthAttemptModel.count)
        row = (await self._session.execute(upsert)).one()
        return AttemptWindow(count=row.count, resets_at_ms=row.window_start_ms + window_ms)

    async def reset(self, scope: str, subject: str) -> None:
        await self._session.execute(delete(AuthAttemptModel).where(AuthAttemptModel.key == self._key(scope, subject)))

    async def purge(self, started_before_ms: int) -> None:
        await self._session.execute(delete(AuthAttemptModel).where(AuthAttemptModel.window_start_ms < started_before_ms))
