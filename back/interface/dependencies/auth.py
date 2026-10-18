from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from application.blindtest.blindtest_command_usecase import BlindtestCommandUseCase
from application.game_night.game_night_command_usecase import GameNightCommandUseCase
from application.game_night.game_night_query_usecase import GameNightQueryUseCase
from interface.dependencies.container import (
    authorize_client,
    authorize_hardware_token,
    game_night_query_usecase,
    game_use_cases,
    realtime_dispatcher,
    websocket_hub,
)
from interface.realtime.dispatcher import RealtimeDispatcher
from interface.realtime.hub import WebSocketHub

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
OptionalControllerToken = Annotated[Optional[str], Header(alias=CONTROLLER_TOKEN_HEADER)]


def require_controller_token(token: OptionalControllerToken = None) -> None:
    if not authorize_client("controller", token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton régie invalide.")


def require_hardware_token(token: Annotated[Optional[str], Header(alias=HARDWARE_TOKEN_HEADER)] = None) -> None:
    if not authorize_hardware_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton matériel invalide.")
