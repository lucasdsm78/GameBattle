from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from application.accounts.account_usecase import AccountUseCase
from application.rooms.room_usecase import RoomUseCase
from application.shared.player_identity import PlayerIdentity
from application.blindtest.blindtest_command_usecase import BlindtestCommandUseCase
from application.game_night.game_night_command_usecase import GameNightCommandUseCase
from application.game_night.game_night_query_usecase import GameNightQueryUseCase
from interface.dependencies.container import (
    account_usecase,
    authorize_client,
    authorize_hardware_token,
    game_night_query_usecase,
    game_use_cases,
    realtime_dispatcher,
    room_broadcaster,
    room_hub,
    room_usecase,
    websocket_hub,
)
from interface.realtime.dispatcher import RealtimeDispatcher
from interface.realtime.hub import WebSocketHub
from interface.realtime.room_broadcaster import RoomBroadcaster
from interface.realtime.room_hub import RoomHub

CONTROLLER_TOKEN_HEADER = "X-GameBattle-Controller-Token"
HARDWARE_TOKEN_HEADER = "X-GameBattle-Hardware-Token"


def game_night_use_case() -> GameNightCommandUseCase:
    return game_use_cases().game_night


def blindtest_use_case() -> BlindtestCommandUseCase:
    return game_use_cases().blindtest


GameNightUseCaseDep = Annotated[GameNightCommandUseCase, Depends(game_night_use_case)]
BlindtestUseCaseDep = Annotated[BlindtestCommandUseCase, Depends(blindtest_use_case)]
DispatcherDep = Annotated[RealtimeDispatcher, Depends(realtime_dispatcher)]
GameNightQueryDep = Annotated[GameNightQueryUseCase, Depends(game_night_query_usecase)]
WebSocketHubDep = Annotated[WebSocketHub, Depends(websocket_hub)]
AccountUseCaseDep = Annotated[AccountUseCase, Depends(account_usecase)]
RoomUseCaseDep = Annotated[RoomUseCase, Depends(room_usecase)]
RoomHubDep = Annotated[RoomHub, Depends(room_hub)]
RoomBroadcasterDep = Annotated[RoomBroadcaster, Depends(room_broadcaster)]


async def current_player(request: Request, accounts: AccountUseCaseDep) -> PlayerIdentity:
    """Le joueur de la session (cookie HttpOnly), sinon 401 : la seule porte des autres modules vers les comptes."""
    from interface.http_session import session_token  # import local : http_session dépend lui-même du container

    return (await accounts.current(session_token(request.cookies))).account.identity


CurrentPlayerDep = Annotated[PlayerIdentity, Depends(current_player)]
OptionalControllerToken = Annotated[Optional[str], Header(alias=CONTROLLER_TOKEN_HEADER)]


def require_controller_token(token: OptionalControllerToken = None) -> None:
    if not authorize_client("controller", token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton régie invalide.")


def require_hardware_token(token: Annotated[Optional[str], Header(alias=HARDWARE_TOKEN_HEADER)] = None) -> None:
    if not authorize_hardware_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton matériel invalide.")
