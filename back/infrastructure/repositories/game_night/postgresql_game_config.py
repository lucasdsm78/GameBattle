from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import inspect, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domain.game_night.models.game_config import GameConfig, build_default_game_config
from domain.game_night.repositories.game_config_repository import GameConfigRepository
from exceptions import ConcurrentModificationError
from infrastructure.database.database import Database
from infrastructure.database.game_sessions.game_session_model import GameSessionModel
from infrastructure.repositories.game_night.game_config_mapper import (
    GameSessionRecord,
    game_config_from_payload,
    game_config_to_payload,
    join_payload,
    split_payload,
)
from infrastructure.repositories.game_night.game_state_repositories import (
    GAME_STATE_REPOSITORIES,
)

_SESSION_ID = "current"  # une seule partie aujourd'hui ; demain, une par salon
_LEGACY_TABLE = "game_config_state"  # ancien document unique, avant les tables par jeu
_COMMON_COLUMNS = tuple(
    column.name for column in GameSessionModel.__table__.columns if column.name not in {"id", "version", "created_at", "saved_at"}
)


@dataclass(frozen=True, slots=True)
class _Snapshot:
    """Ce que la base contient d'après notre dernière lecture ou écriture : documents et versions attendues."""

    record: GameSessionRecord
    session_version: int
    game_versions: dict[str, int]


class PostgreSQLGameConfigRepository(GameConfigRepository):
    """La partie en base : une ligne commune (`game_sessions`) et une ligne par jeu (`<jeu>_games`), en une transaction.

    - Seules les lignes qui ont changé sont écrites : pendant une manche, la ligne commune et celle du jeu en cours.
    - Verrou optimiste à chaque écriture (ligne commune et lignes de jeu) : si une version a changé depuis notre
      lecture, rien n'est écrit, `ConcurrentModificationError` est levée et la prochaine lecture repart de la base.
    """

    def __init__(self, database: Database, session_id: str = _SESSION_ID) -> None:
        self._database = database
        self._session_id = session_id
        self._snapshot: Optional[_Snapshot] = None

    async def get_current(self) -> GameConfig:
        async with self._database.session() as session:
            row = await session.get(GameSessionModel, self._session_id)
            if row is not None:
                stored = {
                    key: state
                    for key, repository in GAME_STATE_REPOSITORIES.items()
                    if (state := await repository.load(session, self._session_id)) is not None
                }
                record = GameSessionRecord(
                    common={name: getattr(row, name) for name in _COMMON_COLUMNS},
                    game_states={key: state.document for key, state in stored.items()},
                )
                config = game_config_from_payload(join_payload(record), {key: state.schema_version for key, state in stored.items()})
                self._snapshot = _Snapshot(record, row.version, {key: state.version for key, state in stored.items()})
                return config

            legacy = await self._legacy_payload(session)
            config = game_config_from_payload(legacy) if legacy is not None else build_default_game_config()
            snapshot = await self._write(session, split_payload(game_config_to_payload(config)), previous=None)
        self._snapshot = snapshot
        return config

    async def save(self, game_config: GameConfig) -> GameConfig:
        record = split_payload(game_config_to_payload(game_config))
        try:
            async with self._database.session() as session:
                snapshot = await self._write(session, record, previous=self._snapshot)
        except ConcurrentModificationError:
            self._snapshot = None  # la base a changé sans nous : la relire avant toute nouvelle écriture
            raise
        self._snapshot = snapshot  # après la validation de la transaction seulement
        return game_config

    async def _write(self, session: AsyncSession, record: GameSessionRecord, previous: Optional[_Snapshot]) -> _Snapshot:
        now = datetime.now(timezone.utc)
        if previous is None:
            session.add(GameSessionModel(id=self._session_id, version=1, created_at=now, saved_at=now, **record.common))
            try:
                await session.flush()
            except IntegrityError as exc:  # créée entre-temps par une autre écriture
                raise ConcurrentModificationError() from exc
            session_version = 1
        else:
            result = await session.execute(
                update(GameSessionModel)
                .where(GameSessionModel.id == self._session_id, GameSessionModel.version == previous.session_version)
                .values(**record.common, version=GameSessionModel.version + 1, saved_at=now)
            )
            if result.rowcount != 1:
                raise ConcurrentModificationError()
            session_version = previous.session_version + 1

        game_versions = dict(previous.game_versions) if previous else {}
        for game_key, document in record.game_states.items():
            if previous is not None and previous.record.game_states.get(game_key) == document:
                continue
            repository = GAME_STATE_REPOSITORIES[game_key]
            if game_key in game_versions:
                game_versions[game_key] = await repository.update(session, self._session_id, document, game_versions[game_key])
            else:
                game_versions[game_key] = await repository.insert(session, self._session_id, document)
        return _Snapshot(record, session_version, game_versions)

    async def _legacy_payload(self, session: AsyncSession) -> Optional[dict[str, Any]]:
        """Base créée par l'API avant les tables par jeu (développement, sans migration) : on reprend une fois
        l'ancien document, qui reste en place. En production, ce sont les migrations qui recopient les données."""
        if not await session.run_sync(lambda sync_session: inspect(sync_session.connection()).has_table(_LEGACY_TABLE)):
            return None
        payload = await session.scalar(text(f"SELECT payload FROM {_LEGACY_TABLE} WHERE aggregate_key = :key"), {"key": self._session_id})
        return json.loads(payload) if isinstance(payload, str) else payload
