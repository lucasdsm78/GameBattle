from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from application.commands.blindtest import BlindtestCommandUseCase
from application.commands.session import SessionCommandUseCase
from application.queries.game_config import GameConfigQueryService
from interface.dependencies.container import (
    authorize_client,
    authorize_hardware_token,
    game_config_query_service,
    game_use_cases,
    realtime_dispatcher,
    websocket_hub,
)
from interface.realtime.dispatcher import RealtimeDispatcher
from interface.realtime.hub import WebSocketHub

CONTROLLER_TOKEN_HEADER = "X-GameBattle-Controller-Token"
HARDWARE_TOKEN_HEADER = "X-GameBattle-Hardware-Token"



def session_use_case() -> SessionCommandUseCase:
    return game_use_cases().session


def blindtest_use_case() -> BlindtestCommandUseCase:
    return game_use_cases().blindtest


SessionUseCaseDep = Annotated[SessionCommandUseCase, Depends(session_use_case)]
BlindtestUseCaseDep = Annotated[BlindtestCommandUseCase, Depends(blindtest_use_case)]
DispatcherDep = Annotated[RealtimeDispatcher, Depends(realtime_dispatcher)]
QueryServiceDep = Annotated[GameConfigQueryService, Depends(game_config_query_service)]
WebSocketHubDep = Annotated[WebSocketHub, Depends(websocket_hub)]
OptionalControllerToken = Annotated[Optional[str], Header(alias=CONTROLLER_TOKEN_HEADER)]


def require_controller_token(token: OptionalControllerToken = None) -> None:
    if not authorize_client("controller", token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton régie invalide.")


def require_hardware_token(token: Annotated[Optional[str], Header(alias=HARDWARE_TOKEN_HEADER)] = None) -> None:
    if not authorize_hardware_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton matériel invalide.")
