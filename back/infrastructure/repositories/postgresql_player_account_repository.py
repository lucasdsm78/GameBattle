from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.pseudo import Pseudo
from domain.accounts.repositories.player_account_repository import (
    PlayerAccountRepository,
)
from exceptions import PseudoAlreadyTakenError
from infrastructure.database.models import PlayerAccountModel


def _to_domain(row: PlayerAccountModel) -> PlayerAccount:
    return PlayerAccount(id=row.id, pseudo=Pseudo(row.pseudo), password_hash=row.password_hash, created_at_ms=row.created_at_ms)


class PostgreSQLPlayerAccountRepository(PlayerAccountRepository):
    """Travaille dans la transaction de l'unité de travail qui l'a créé : il ne valide jamais lui-même."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, account_id: str) -> Optional[PlayerAccount]:
        row = await self._session.get(PlayerAccountModel, account_id)
        return _to_domain(row) if row else None

    async def find_by_pseudo(self, pseudo: Pseudo) -> Optional[PlayerAccount]:
        row = await self._session.scalar(select(PlayerAccountModel).where(PlayerAccountModel.pseudo_key == pseudo.key))
        return _to_domain(row) if row else None

    async def add(self, account: PlayerAccount) -> None:
        self._session.add(
            PlayerAccountModel(
                id=account.id,
                pseudo=account.pseudo.value,
                pseudo_key=account.pseudo.key,
                password_hash=account.password_hash,
                created_at_ms=account.created_at_ms,
            )
        )
        try:
            await self._session.flush()  # la contrainte d'unicité se déclenche ici, pas au commit
        except IntegrityError as exc:
            raise PseudoAlreadyTakenError("Ce pseudo est déjà pris.") from exc

    async def save_password_hash(self, account: PlayerAccount) -> None:
        await self._session.execute(
            update(PlayerAccountModel).where(PlayerAccountModel.id == account.id).values(password_hash=account.password_hash)
        )
