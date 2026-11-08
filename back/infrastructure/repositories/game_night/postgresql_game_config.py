from __future__ import annotations

import json
from typing import Any, Optional

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.game_night.models.game_config import GameConfig, build_default_game_config
from domain.game_night.repositories.game_config_repository import GameConfigRepository
from infrastructure.database.database import Database
from infrastructure.database.models.game_night.game_night_model import GameNightModel
from infrastructure.database.upsert import upsert_insert
from infrastructure.repositories.game_night.game_config_mapper import (
    GameNightRecord,
    game_config_from_payload,
    game_config_to_payload,
    join_payload,
    split_payload,
)
from infrastructure.repositories.game_night.game_state_tables import GAME_STATE_TABLES

NIGHT_ID = "current"  # une seule soirée aujourd'hui ; demain, une par salon
GAME_STATE_SCHEMA_VERSION = 1
LEGACY_TABLE = "game_config_state"  # ancien document unique, avant les tables par jeu
_NIGHT_COLUMNS = tuple(column.name for column in GameNightModel.__table__.columns if column.name not in {"id", "revision"})


class PostgreSQLGameConfigRepository(GameConfigRepository):
    """La soirée en base : une ligne commune (`game_nights`) et une ligne par jeu (`<jeu>_games`), dans une transaction.

    Seules les lignes qui ont changé sont écrites : pendant une manche, la ligne commune (qui porte la révision)
    et celle du jeu en cours. Valable car l'API tourne en un seul processus (`SingleInstanceLock`).
    """

    def __init__(self, database: Database, night_id: str = NIGHT_ID) -> None:
        self._database = database
        self._night_id = night_id
        self._persisted: Optional[GameNightRecord] = None  # ce que la base contient, d'après notre dernière lecture/écriture

    async def get_current(self) -> GameConfig:
        async with self._database.session() as session:
            night = await session.get(GameNightModel, self._night_id)
            if night is not None:
                record = GameNightRecord(
                    night={name: getattr(night, name) for name in _NIGHT_COLUMNS},
                    game_states={
                        key: row.state
                        for key, model in GAME_STATE_TABLES.items()
                        if (row := await session.get(model, self._night_id)) is not None
                    },
                )
                self._persisted = record
                return game_config_from_payload(join_payload(record))

            legacy = await self._legacy_payload(session)
            config = game_config_from_payload(legacy) if legacy is not None else build_default_game_config()
            record = split_payload(game_config_to_payload(config))
            await self._write(session, record, previous=None)
        self._persisted = record
        return config

    async def save(self, game_config: GameConfig) -> GameConfig:
        record = split_payload(game_config_to_payload(game_config))
        async with self._database.session() as session:
            await self._write(session, record, previous=self._persisted)
        self._persisted = record  # après la validation de la transaction seulement
        return game_config

    async def _write(self, session: AsyncSession, record: GameNightRecord, previous: Optional[GameNightRecord]) -> None:
        night = upsert_insert(session, GameNightModel).values(id=self._night_id, revision=1, **record.night)
        await session.execute(
            night.on_conflict_do_update(index_elements=[GameNightModel.id], set_={**record.night, "revision": GameNightModel.revision + 1})
        )
        for game_key, state in record.game_states.items():
            if previous is not None and previous.game_states.get(game_key) == state:
                continue
            model = GAME_STATE_TABLES[game_key]
            row = upsert_insert(session, model).values(night_id=self._night_id, state=state, schema_version=GAME_STATE_SCHEMA_VERSION)
            await session.execute(
                row.on_conflict_do_update(index_elements=[model.night_id], set_={"state": state, "schema_version": GAME_STATE_SCHEMA_VERSION})
            )

    async def _legacy_payload(self, session: AsyncSession) -> Optional[dict[str, Any]]:
        """Base créée par l'API avant les tables par jeu (développement, sans migration) : on reprend une fois
        l'ancien document, qui reste en place. En production, c'est la migration 0003 qui recopie les données."""
        if not await session.run_sync(lambda sync_session: inspect(sync_session.connection()).has_table(LEGACY_TABLE)):
            return None
        payload = await session.scalar(text(f"SELECT payload FROM {LEGACY_TABLE} WHERE aggregate_key = :key"), {"key": self._night_id})
        return json.loads(payload) if isinstance(payload, str) else payload
