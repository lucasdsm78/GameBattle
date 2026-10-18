from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update

from domain.models.game_config import GameConfig, build_default_game_config
from domain.repositories.game_config import GameConfigRepository
from infrastructure.database.database import Database
from infrastructure.database.models import GameConfigStateModel
from infrastructure.repositories.game_config_mapper import game_config_from_payload

AGGREGATE_KEY = "current"


def _checksum(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _new_row(payload: dict[str, Any], source: str) -> GameConfigStateModel:
    return GameConfigStateModel(aggregate_key=AGGREGATE_KEY, payload=payload, checksum=_checksum(payload), source=source)


class PostgreSQLGameConfigRepository(GameConfigRepository):
    def __init__(self, database: Database) -> None:
        self._database = database

    async def get_current(self) -> GameConfig:
        async with self._database.session() as session:
            payload = await session.scalar(
                select(GameConfigStateModel.payload).where(GameConfigStateModel.aggregate_key == AGGREGATE_KEY)
            )
            if payload is not None:
                return game_config_from_payload(payload)
            default_config = build_default_game_config()
            session.add(_new_row(default_config.to_dict(), source="bootstrap"))
            return default_config

    async def save(self, game_config: GameConfig) -> GameConfig:
        payload = game_config.to_dict()
        async with self._database.session() as session:
            result = await session.execute(
                update(GameConfigStateModel)
                .where(GameConfigStateModel.aggregate_key == AGGREGATE_KEY)
                .values(
                    payload=payload,
                    checksum=_checksum(payload),
                    revision=GameConfigStateModel.revision + 1,
                    source="api",
                    updated_at=datetime.now(timezone.utc),
                )
            )
            if result.rowcount == 0:
                session.add(_new_row(payload, source="api"))
        return game_config
