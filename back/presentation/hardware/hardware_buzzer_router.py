from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from application.game_config.game_config_command_usecase import GameConfigCommandUseCase
from application.game_config.game_config_models import BlindtestBuzzerCommandModel, GameConfigReadModel
from dependency_injections import authorize_hardware_token, game_config_command_usecase

router = APIRouter(prefix="/api/hardware", tags=["hardware"])


@router.post("/buzzer-events", response_model=GameConfigReadModel, summary="Recevoir un buzz matériel USB")
async def receive_hardware_buzzer_event(
    payload: BlindtestBuzzerCommandModel,
    hardware_token: str | None = Header(default=None, alias="X-GameBattle-Hardware-Token"),
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    if not authorize_hardware_token(hardware_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton matériel invalide.")
    return await command_usecase.register_blindtest_buzzer(payload)

