from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from application.game_config.command import GameConfigCommandUseCase
from application.game_config.game_config_models import GameConfigReadModel
from application.game_config.game_config_query_usecase import GameConfigQueryUseCase
from dependency_injections import (
    authorize_client,
    game_config_command_usecase,
    game_config_query_usecase,
    websocket_hub_singleton,
)
from infrastructure.realtime.websocket_hub import WebSocketHub
from presentation.realtime.game_config_ws_handler import (
    build_broadcast_envelopes,
    build_client_envelope,
    dispatch_game_config_event,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["realtime"])


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
        await websocket.send_json(build_client_envelope("game.config.snapshot", current, client_type))

        while True:
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Message JSON invalide."})
                continue

            event_type = str(message.get("type", ""))
            if not event_type:
                await websocket.send_json({"type": "error", "detail": "Type d'évènement manquant."})
                continue

            payload = message.get("payload") or {}
            if not isinstance(payload, dict):
                await websocket.send_json({"type": "error", "detail": "Payload JSON invalide."})
                continue

            result = await dispatch_game_config_event(
                client_type=client_type,
                event_type=event_type,
                payload=payload,
                command_usecase=command_usecase,
            )
            if result is None:
                continue
            if isinstance(result, dict):
                await websocket.send_json(result)
                continue

            updated: GameConfigReadModel = result
            await hub.broadcast_json_by_client_type(build_broadcast_envelopes("game.config.updated", updated))
    except WebSocketDisconnect:
        logger.info("game_config.websocket.disconnected", extra={"client_type": client_type})
    finally:
        await hub.disconnect(client)

