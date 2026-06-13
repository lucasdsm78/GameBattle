from __future__ import annotations

import hashlib
import json

from sqlalchemy import select

from domain.game_config.model.game_config import (
    ActiveRound,
    BlindtestState,
    BlindtestTrack,
    CultureQuestion,
    CultureState,
    GameConfig,
    GameDefinition,
    GameRoundPlan,
    GameSession,
    GameSettings,
    StopChronoState,
    build_default_game_config,
)
from domain.game_config.repository.game_config_repository import GameConfigRepository
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
        session_payload = payload.get("session", {})
        blindtest_payload = session_payload.get("blindtest", {})
        stopchrono_payload = session_payload.get("stopchrono", {})
        culture_payload = session_payload.get("culture", {})
        active_round_payload = session_payload.get("active_round")

        config = GameConfig(
            settings=GameSettings(
                game_title=payload["settings"].get("game_title", "GameBattle Night"),
                random_round_order=payload["settings"].get("random_round_order", True),
                teams=payload["settings"].get("teams", []),
                buzzer_keys=payload["settings"].get("buzzer_keys", []),
                total_rounds=payload["settings"].get("total_rounds", 1),
                culture_difficulty=payload["settings"].get("culture_difficulty", "toutes"),
            ),
            games=[GameDefinition(**game_payload) for game_payload in payload.get("games", [])],
            rounds=[GameRoundPlan(**round_payload) for round_payload in payload["rounds"]],
            session=GameSession(
                active_round=ActiveRound(**active_round_payload) if active_round_payload else None,
                blindtest=BlindtestState(
                    round_id=blindtest_payload.get("round_id", ""),
                    total_tracks=blindtest_payload.get("total_tracks", 0),
                    current_track_index=blindtest_payload.get("current_track_index", 0),
                    current_track=(
                        BlindtestTrack(**blindtest_payload["current_track"])
                        if blindtest_payload.get("current_track")
                        else None
                    ),
                    current_buzzer_team=blindtest_payload.get("current_buzzer_team"),
                    revealed=blindtest_payload.get("revealed", False),
                    playback_state=blindtest_payload.get("playback_state", "stopped"),
                    scores=blindtest_payload.get("scores", {}),
                    winner_team=blindtest_payload.get("winner_team"),
                    tracks=[BlindtestTrack(**track_payload) for track_payload in blindtest_payload.get("tracks", [])],
                    playlist_name=blindtest_payload.get("playlist_name", ""),
                    playlist_source_url=blindtest_payload.get("playlist_source_url", ""),
                    playlist_provider=blindtest_payload.get("playlist_provider", ""),
                ),
                stopchrono=StopChronoState(
                    target_ms=stopchrono_payload.get("target_ms", 0),
                    phase=stopchrono_payload.get("phase", "idle"),
                    current_team_index=stopchrono_payload.get("current_team_index", 0),
                    started_at_ms=stopchrono_payload.get("started_at_ms", 0),
                    results=stopchrono_payload.get("results", {}) or {},
                    scores=stopchrono_payload.get("scores", {}) or {},
                    winner_team=stopchrono_payload.get("winner_team"),
                ),
                culture=CultureState(
                    phase=culture_payload.get("phase", "idle"),
                    current_index=culture_payload.get("current_index", 0),
                    total_questions=culture_payload.get("total_questions", 0),
                    difficulty=culture_payload.get("difficulty", "toutes"),
                    questions=[
                        CultureQuestion(
                            id=q.get("id", ""),
                            question=q.get("question", ""),
                            answer=q.get("answer", ""),
                            explanation=q.get("explanation", ""),
                            difficulty=q.get("difficulty", "toutes"),
                        )
                        for q in (culture_payload.get("questions", []) or [])
                    ],
                    current_buzzer_team=culture_payload.get("current_buzzer_team"),
                    answered=culture_payload.get("answered", False),
                    scores=culture_payload.get("scores", {}) or {},
                    winner_team=culture_payload.get("winner_team"),
                ),
                round_sequence=list(session_payload.get("round_sequence", []) or []),
                round_index=session_payload.get("round_index", 0),
                total_rounds=session_payload.get("total_rounds", 0),
                manches_won=session_payload.get("manches_won", {}) or {},
                manche_finished=session_payload.get("manche_finished", False),
                manche_winner=session_payload.get("manche_winner"),
                final_ranking=list(session_payload.get("final_ranking", []) or []),
                ranking_reveal_count=session_payload.get("ranking_reveal_count", 0),
                updated_at=session_payload.get("updated_at", payload.get("updated_at", "")),
            ),
            status=payload.get("status", "configuring"),
            updated_at=payload.get("updated_at", ""),
        )
        config.validate()
        return config


