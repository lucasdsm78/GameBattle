from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import ConcurrentModificationError
from infrastructure.database.games.shared.game_state_columns import GameStateColumns
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


@dataclass(frozen=True, slots=True)
class StoredGameState:
    document: dict[str, Any]
    schema_version: int
    version: int


class GameStateRepository:
    """Lecture et écriture de la ligne d'un jeu pour une partie, dans la transaction de l'appelant.

    Verrou optimiste : une mise à jour ne passe que si la ligne est encore à la version lue. Sinon, une autre
    écriture a gagné la course : `ConcurrentModificationError`, jamais un écrasement silencieux.
    """

    model: ClassVar[type[GameStateColumns]]
    mapper: ClassVar[GameStateMapper[Any]]

    async def load(self, session: AsyncSession, session_id: str) -> Optional[StoredGameState]:
        model = self.model
        row = (
            await session.execute(select(model.state, model.schema_version, model.version).where(model.session_id == session_id))
        ).first()
        return StoredGameState(row.state, row.schema_version, row.version) if row else None

    async def insert(self, session: AsyncSession, session_id: str, document: dict[str, Any]) -> int:
        session.add(self.model(session_id=session_id, state=document, schema_version=self.mapper.schema_version, version=1))
        try:
            await session.flush()
        except IntegrityError as exc:  # la ligne a été créée entre-temps
            raise ConcurrentModificationError() from exc
        return 1

    async def update(self, session: AsyncSession, session_id: str, document: dict[str, Any], expected_version: int) -> int:
        model = self.model
        result = await session.execute(
            update(model)
            .where(model.session_id == session_id, model.version == expected_version)
            .values(state=document, schema_version=self.mapper.schema_version, version=model.version + 1)
        )
        if result.rowcount != 1:
            raise ConcurrentModificationError()
        return expected_version + 1
