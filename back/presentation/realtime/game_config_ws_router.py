from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from application.game_config.game_config_command_usecase import GameConfigCommandUseCase
from application.game_config.game_config_models import (
    BlindtestAnswerCommandModel,
    BlindtestBuzzerCommandModel,
    BlindtestPlaybackCommandModel,
    BlindtestPlaybackSyncCommandModel,
    BlindtestPlaylistCommandModel,
    CultureDifficultyCommandModel,
    GameConfigEnvelope,
    GameConfigUpsertModel,
    SpotifyPlaylistImportCommandModel,
)
from application.game_config.game_config_query_usecase import GameConfigQueryUseCase
from dependency_injections import (
    authorize_client,
    game_config_command_usecase,
    game_config_query_usecase,
    websocket_hub_singleton,
)
from domain.game_config.exception.game_config_exception import GameConfigurationNotReadyError, InvalidGameConfigError
from infrastructure.realtime.websocket_hub import WebSocketHub

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["realtime"])


def _public_envelope(event_type: str, payload) -> dict:
    """Construit l'enveloppe envoyée aux clients en retirant la séquence des prochains jeux."""
    envelope = GameConfigEnvelope(type=event_type, payload=payload).model_dump()
    session = envelope.get("payload", {}).get("session")
    if isinstance(session, dict):
        session.pop("round_sequence", None)
        culture = session.get("culture")
        if isinstance(culture, dict):
            # On ne révèle pas toutes les questions/réponses à venir aux clients.
            culture.pop("questions", None)
    return envelope


@router.websocket("/game-config")
async def game_config_websocket(
    websocket: WebSocket,
    client_type: str = Query(..., pattern="^(controller|display)$"),
    token: Optional[str] = Query(default=None),
    hub: WebSocketHub = Depends(websocket_hub_singleton),
    query_usecase: GameConfigQueryUseCase = Depends(game_config_query_usecase),
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> None:
    if not authorize_client(client_type=client_type, token=token):
        await websocket.close(code=1008, reason="unauthorized")
        return

    await websocket.accept()
    client = await hub.connect(websocket, client_type)

    try:
        current = await query_usecase.get_current()
        await websocket.send_json(_public_envelope("game.config.snapshot", current))

        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Message JSON invalide."})
                continue

            event_type = message.get("type")
            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if event_type == "spotify.user-token":
                token = str((message.get("payload") or {}).get("access_token", ""))
                await command_usecase.set_spotify_user_token(token)
                continue

            # L'écran (display) peut envoyer le buzz et piloter le chrono (touches clavier).
            display_allowed_events = {"blindtest.buzzer", "stopchrono.start", "stopchrono.stop", "culture.buzzer"}
            if client_type != "controller" and event_type not in display_allowed_events:
                await websocket.send_json({"type": "error", "detail": "Le client display est en lecture seule."})
                continue

            try:
                if event_type == "game.config.replace":
                    payload = GameConfigUpsertModel(**message.get("payload", {}))
                    updated = await command_usecase.replace_config(payload)
                elif event_type == "game.config.launch":
                    updated = await command_usecase.launch_game()
                elif event_type == "blindtest.playlist.load":
                    payload = BlindtestPlaylistCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.load_blindtest_playlist(payload)
                elif event_type == "blindtest.playlist.import-spotify":
                    payload = SpotifyPlaylistImportCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.import_blindtest_playlist_from_spotify(payload)
                elif event_type == "blindtest.playlist.reload":
                    updated = await command_usecase.reload_default_playlist()
                elif event_type == "blindtest.buzzer":
                    payload = BlindtestBuzzerCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.register_blindtest_buzzer(payload)
                elif event_type == "blindtest.answer":
                    payload = BlindtestAnswerCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.answer_blindtest(payload)
                elif event_type == "blindtest.playback.control":
                    payload = BlindtestPlaybackCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.control_blindtest_playback(payload)
                elif event_type == "blindtest.playback.sync":
                    payload = BlindtestPlaybackSyncCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.sync_blindtest_playback(payload)
                elif event_type == "blindtest.next-track":
                    updated = await command_usecase.next_blindtest_track()
                elif event_type == "stopchrono.start":
                    updated = await command_usecase.start_stopchrono()
                elif event_type == "stopchrono.stop":
                    updated = await command_usecase.stop_stopchrono()
                elif event_type == "stopchrono.next-team":
                    updated = await command_usecase.next_stopchrono_team()
                elif event_type == "culture.start":
                    updated = await command_usecase.start_culture()
                elif event_type == "culture.select-difficulty":
                    payload = CultureDifficultyCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.select_culture_difficulty(payload)
                elif event_type == "culture.buzzer":
                    payload = BlindtestBuzzerCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.register_culture_buzzer(payload)
                elif event_type == "culture.answer":
                    payload = BlindtestAnswerCommandModel(**message.get("payload", {}))
                    updated = await command_usecase.answer_culture(payload)
                elif event_type == "culture.next-question":
                    updated = await command_usecase.next_culture_question()
                elif event_type == "game.next-manche":
                    updated = await command_usecase.next_manche()
                elif event_type == "ranking.reveal-next":
                    updated = await command_usecase.reveal_next_ranking()
                else:
                    await websocket.send_json({"type": "error", "detail": "Type d'évènement non supporté."})
                    continue
            except InvalidGameConfigError as exc:
                await websocket.send_json({"type": "error", "detail": exc.message})
                continue
            except GameConfigurationNotReadyError as exc:
                await websocket.send_json({"type": "error", "detail": exc.message})
                continue
            except Exception:
                logger.exception("game_config.websocket.replace_failed")
                await websocket.send_json({"type": "error", "detail": "Erreur interne lors de la mise à jour."})
                continue

            event = _public_envelope("game.config.updated", updated)
            await hub.broadcast_json(event)
    except WebSocketDisconnect:
        logger.info("game_config.websocket.disconnected", extra={"client_type": client_type})
    finally:
        await hub.disconnect(client)

