from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import suppress
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from application.accounts.account_query_usecase import AccountQueryUseCase
from application.rooms.presenters.room_view import room_view
from application.shared.player_identity import PlayerIdentity
from exceptions import NotAuthenticatedError
from interface.dependencies import (
    AccountQueryUseCaseDep,
    RoomBroadcasterDep,
    RoomHubDep,
    RoomQueryUseCaseDep,
)
from interface.http_session import announced_origin, origin_is_trusted, session_token
from interface.realtime.constants.realtime_limits import ROOM_MESSAGE_MAX_CHARS
from interface.realtime.constants.realtime_timing import HEARTBEAT_SECONDS, IDLE_TIMEOUT_SECONDS, SESSION_RECHECK_SECONDS
from interface.realtime.constants.websocket_codes import CLOSE_IDLE, CLOSE_NOT_IN_ROOM, CLOSE_TOO_CHATTY, CLOSE_UNAUTHENTICATED
from interface.realtime.message_handler import RateLimiter
from interface.realtime.room_connection import RoomConnection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["realtime"])


async def _resolve_player(accounts: AccountQueryUseCase, token: Optional[str]) -> Optional[PlayerIdentity]:
    try:
        return (await accounts.current(token)).account.identity
    except NotAuthenticatedError:
        return None


async def _heartbeat(connection: RoomConnection, accounts: AccountQueryUseCase, token: Optional[str]) -> None:
    """Ping régulier ; coupe une connexion muette ou dont la session n'est plus valide."""
    session_checked_at = time.monotonic()
    while not connection.closed:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        now = time.monotonic()
        if now - connection.last_seen > IDLE_TIMEOUT_SECONDS:
            await connection.close(CLOSE_IDLE, "inactive")
            return
        if now - session_checked_at > SESSION_RECHECK_SECONDS:
            if await _resolve_player(accounts, token) is None:
                await connection.close(CLOSE_UNAUTHENTICATED, "session expirée")
                return
            session_checked_at = now
        connection.send({"type": "ping"})


@router.websocket("/rooms/current")
async def room_socket(
    websocket: WebSocket, accounts: AccountQueryUseCaseDep, rooms: RoomQueryUseCaseDep, hub: RoomHubDep, broadcaster: RoomBroadcasterDep
) -> None:
    """Flux temps réel du salon du joueur connecté.

    1. Poignée de main : origine de confiance (sinon refus avant tout : protection contre le détournement de
       WebSocket entre sites), session valide (cookie HttpOnly), appartenance à un salon.
    2. État complet à la connexion et à chaque reconnexion (resynchronisation), puis mises à jour poussées.
    3. Ping toutes les 20 s, connexion muette coupée après 50 s, débit limité, session revérifiée chaque minute.
    """
    if not origin_is_trusted(announced_origin(websocket.headers), websocket.headers.get("host")):
        await websocket.close(code=1008)  # avant `accept` : le navigateur d'un autre site n'obtient rien
        return
    token = session_token(websocket.cookies)
    player = await _resolve_player(accounts, token)
    room = await rooms.current_room(player) if player else None
    await websocket.accept()  # accepter puis fermer avec un code explicite : le client sait qu'il ne doit pas insister
    if player is None or room is None:
        await websocket.close(code=CLOSE_UNAUTHENTICATED if player is None else CLOSE_NOT_IN_ROOM)
        return

    connection = hub.connect(websocket, room.id, player.account_id)
    heartbeat: Optional[asyncio.Task[None]] = None
    # Tout ce qui suit l'enregistrement est dans le `try` : une erreur (base indisponible pendant la diffusion de
    # présence…) ne laisse jamais une connexion fantôme dans le hub, ni un joueur affiché en ligne à tort.
    try:
        connection.send({"type": "room.snapshot", "room": room_view(room, player.account_id, hub.online(room.id))})
        await broadcaster.broadcast(room.id)  # présence : les autres voient qu'il est en ligne
        heartbeat = asyncio.create_task(_heartbeat(connection, accounts, token))
        limiter = RateLimiter(rate_per_second=2.0, burst=10)
        while not connection.closed:
            raw = await websocket.receive_text()
            connection.last_seen = time.monotonic()
            if len(raw) > ROOM_MESSAGE_MAX_CHARS or not limiter.allow():
                await connection.close(CLOSE_TOO_CHATTY, "trop de messages")
                break
            with suppress(ValueError, AttributeError):
                if json.loads(raw).get("type") == "resync":
                    current = await rooms.current_room(player)
                    if current is None or current.id != room.id:
                        await connection.close(CLOSE_NOT_IN_ROOM, "plus membre du salon")
                        break
                    connection.send({"type": "room.snapshot", "room": room_view(current, player.account_id, hub.online(room.id))})
    except WebSocketDisconnect:
        pass
    except (KeyError, RuntimeError):  # trame binaire ou socket déjà fermée
        pass
    finally:
        if heartbeat is not None:
            heartbeat.cancel()
        hub.remove(connection)
        broadcaster.broadcast_soon(room.id)  # présence : il n'est plus en ligne (même si cette tâche est annulée)
        await connection.close()
