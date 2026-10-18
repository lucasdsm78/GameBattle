from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from application.game_config.snapshot import ClientRole
from infrastructure.realtime.websocket_hub import encode_snapshot
from presentation.dependencies import CommandBusDep, QueryServiceDep, WebSocketHubDep, authorize_client
from presentation.realtime.game_config_ws_handler import RateLimiter, error_reply, handle_client_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["realtime"])


@router.websocket("/game-config")
async def game_config_websocket(
    websocket: WebSocket,
    hub: WebSocketHubDep,
    query: QueryServiceDep,
    bus: CommandBusDep,
    client_type: Literal["controller", "display"] = Query(...),
    token: Optional[str] = Query(default=None, max_length=256),
) -> None:
    if not authorize_client(client_type, token):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="unauthorized")
        return

    await websocket.accept()
    role = ClientRole(client_type)
    channel = hub.connect(websocket, role)
    limiter = RateLimiter()
    try:
        snapshot = await query.get_current()
        channel.push_snapshot(snapshot.revision, encode_snapshot("game.config.snapshot", snapshot, role))
        while True:
            raw = await websocket.receive_text()
            reply = await handle_client_message(raw, role, bus) if limiter.allow() else error_reply("Trop de messages : ralentis.")
            if reply is not None:
                channel.push_reply(reply)
    except WebSocketDisconnect:
        logger.info("game_config.websocket.disconnected", extra={"client_type": client_type})
    except KeyError:
        # Trame binaire : seul le texte JSON est accepté.
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
    finally:
        await hub.disconnect(channel)
