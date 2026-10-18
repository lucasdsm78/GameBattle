from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from application.commands.bus import GameCommandBus
from application.queries.game_config import GameConfigQueryService
from interface.dependencies.container import (
    authorize_client,
    authorize_hardware_token,
    game_command_bus,
    game_config_query_service,
    websocket_hub,
)
from interface.realtime.hub import WebSocketHub

CONTROLLER_TOKEN_HEADER = "X-GameBattle-Controller-Token"
HARDWARE_TOKEN_HEADER = "X-GameBattle-Hardware-Token"

CommandBusDep = Annotated[GameCommandBus, Depends(game_command_bus)]
QueryServiceDep = Annotated[GameConfigQueryService, Depends(game_config_query_service)]
WebSocketHubDep = Annotated[WebSocketHub, Depends(websocket_hub)]
OptionalControllerToken = Annotated[Optional[str], Header(alias=CONTROLLER_TOKEN_HEADER)]


def require_controller_token(token: OptionalControllerToken = None) -> None:
    if not authorize_client("controller", token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton régie invalide.")


def require_hardware_token(token: Annotated[Optional[str], Header(alias=HARDWARE_TOKEN_HEADER)] = None) -> None:
    if not authorize_hardware_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton matériel invalide.")
