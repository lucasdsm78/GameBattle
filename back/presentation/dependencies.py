from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status

from application.game_config.command import GameConfigCommandUseCase
from application.game_config.game_config_query_usecase import GameConfigQueryUseCase
from dependency_injections import (
    authorize_client,
    authorize_hardware_token,
    game_config_command_usecase,
    game_config_query_usecase,
    websocket_hub_singleton,
)
from infrastructure.realtime.websocket_hub import WebSocketHub

GameConfigCommandDep = Annotated[GameConfigCommandUseCase, Depends(game_config_command_usecase)]
GameConfigQueryDep = Annotated[GameConfigQueryUseCase, Depends(game_config_query_usecase)]
WebSocketHubDep = Annotated[WebSocketHub, Depends(websocket_hub_singleton)]


def require_hardware_token(
    hardware_token: Optional[str] = Header(default=None, alias="X-GameBattle-Hardware-Token"),
) -> None:
    if not authorize_hardware_token(hardware_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton matériel invalide.")


HardwareAuthDep = Annotated[None, Depends(require_hardware_token)]

__all__ = [
    "GameConfigCommandDep",
    "GameConfigQueryDep",
    "HardwareAuthDep",
    "WebSocketHubDep",
    "authorize_client",
]

