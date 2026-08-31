from __future__ import annotations

from domain.game_config.model.game_config import (
    ActiveRound,
    BlindtestState,
    BlindtestTrack,
    BombeState,
    CultureQuestion,
    CultureState,
    GameConfig,
    GameDefinition,
    GameRoundPlan,
    GameSession,
    GameSettings,
    StopChronoState,
)


def game_config_from_payload(payload: dict) -> GameConfig:
    teams_payload = list(payload["settings"].get("teams", []))
    session_payload = payload.get("session", {})
    blindtest_payload = session_payload.get("blindtest", {})
    stopchrono_payload = session_payload.get("stopchrono", {})
    culture_payload = session_payload.get("culture", {})
    bombe_payload = session_payload.get("bombe", {})
    active_round_payload = session_payload.get("active_round")

    config = GameConfig(
        settings=GameSettings(
            game_title=payload["settings"].get("game_title", "GameBattle Night"),
            random_round_order=payload["settings"].get("random_round_order", True),
            teams=teams_payload,
            buzzer_keys=payload["settings"].get("buzzer_keys", []),
            total_rounds=payload["settings"].get("total_rounds", 1),
            culture_difficulty=payload["settings"].get("culture_difficulty", "toutes"),
        ),
        games=[GameDefinition(**game_payload) for game_payload in payload.get("games", [])],
        rounds=[GameRoundPlan(**round_payload) for round_payload in payload.get("rounds", [])],
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
                scores=blindtest_payload.get("scores", {}) or {},
                winner_team=blindtest_payload.get("winner_team"),
                tracks=[BlindtestTrack(**track_payload) for track_payload in blindtest_payload.get("tracks", [])],
                playlist_name=blindtest_payload.get("playlist_name", ""),
                playlist_source_url=blindtest_payload.get("playlist_source_url", ""),
                playlist_provider=blindtest_payload.get("playlist_provider", ""),
                playback_position_ms=blindtest_payload.get("playback_position_ms", 0),
                playback_duration_ms=blindtest_payload.get("playback_duration_ms", 0),
                playback_updated_at=blindtest_payload.get("playback_updated_at", payload.get("updated_at", "")),
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
                current_question=(
                    CultureQuestion(
                        id=culture_payload["current_question"].get("id", ""),
                        question=culture_payload["current_question"].get("question", ""),
                        answer=culture_payload["current_question"].get("answer", ""),
                        explanation=culture_payload["current_question"].get("explanation", ""),
                        difficulty=culture_payload["current_question"].get("difficulty", "toutes"),
                    )
                    if culture_payload.get("current_question")
                    else None
                ),
                asked_questions=list(culture_payload.get("asked_questions", []) or []),
                current_buzzer_team=culture_payload.get("current_buzzer_team"),
                answered=culture_payload.get("answered", False),
                scores=culture_payload.get("scores", {}) or {},
                winner_team=culture_payload.get("winner_team"),
            ),
            bombe=BombeState(
                phase=bombe_payload.get("phase", "idle"),
                letter=bombe_payload.get("letter", ""),
                current_team_index=bombe_payload.get("current_team_index", 0),
                turn_history=list(bombe_payload.get("turn_history", []) or []),
                started_at_ms=bombe_payload.get("started_at_ms", 0),
                deadline_at_ms=bombe_payload.get("deadline_at_ms", 0),
                exploded_team=bombe_payload.get("exploded_team"),
                winner_team=bombe_payload.get("winner_team"),
                scores=bombe_payload.get("scores", {}) or {team: 0 for team in teams_payload},
                eligible_team_indices=list(
                    bombe_payload.get("eligible_team_indices", [])
                    or (range(len(teams_payload)) if bombe_payload.get("phase") == "running" else [])
                ),
                tiebreak_round=bombe_payload.get("tiebreak_round", 0),
                sound=bombe_payload.get("sound", ""),
                die_result=bombe_payload.get("die_result", ""),
                roller_team_index=bombe_payload.get("roller_team_index"),
                die_reveal_at_ms=bombe_payload.get("die_reveal_at_ms", 0),
            ),
            round_sequence=list(session_payload.get("round_sequence", []) or []),
            round_index=session_payload.get("round_index", 0),
            total_rounds=session_payload.get("total_rounds", 0),
            manches_won=session_payload.get("manches_won", {}) or {},
            manche_finished=session_payload.get("manche_finished", False),
            manche_winner=session_payload.get("manche_winner"),
            final_ranking=list(session_payload.get("final_ranking", []) or []),
            ranking_reveal_count=session_payload.get("ranking_reveal_count", 0),
            last_bombe_roller_index=session_payload.get("last_bombe_roller_index"),
            updated_at=session_payload.get("updated_at", payload.get("updated_at", "")),
        ),
        status=payload.get("status", "configuring"),
        updated_at=payload.get("updated_at", ""),
    )
    config.validate()
    return config
