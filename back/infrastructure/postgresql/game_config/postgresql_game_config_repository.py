from __future__ import annotations

import hashlib
import json

from sqlalchemy import select

from domain.game_config.model.game_config import GameConfig, build_default_game_config
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.game_config_payload_mapper import game_config_from_payload
from infrastructure.postgresql.database import session_scope
from infrastructure.postgresql.models import GameConfigStateModel


class PostgreSQLGameConfigRepository(GameConfigRepository):
    async def get_current(self) -> GameConfig:
        async with session_scope() as session:
            result = await session.execute(
                select(GameConfigStateModel).where(GameConfigStateModel.aggregate_key == "current")
            )
            row = result.scalar_one_or_none()
            if row is None:
                default_config = build_default_game_config()
                payload = default_config.to_dict()
                session.add(
                    GameConfigStateModel(
                        aggregate_key="current",
                        payload=payload,
                        checksum=self._checksum(payload),
                        source="bootstrap",
                    )
                )
                await session.flush()
                return default_config
            return self._to_domain(row.payload)

    async def save(self, game_config: GameConfig) -> GameConfig:
        payload = game_config.to_dict()
        async with session_scope() as session:
            result = await session.execute(
                select(GameConfigStateModel).where(GameConfigStateModel.aggregate_key == "current")
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = GameConfigStateModel(
                    aggregate_key="current",
                    payload=payload,
                    checksum=self._checksum(payload),
                    source="api",
                )
                session.add(row)
            else:
                row.payload = payload
                row.revision += 1
                row.checksum = self._checksum(payload)
                row.source = "api"
            await session.flush()
        return game_config

    def _checksum(self, payload: dict) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def _to_domain(self, payload: dict) -> GameConfig:
        return game_config_from_payload(payload)


