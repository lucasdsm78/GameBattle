from __future__ import annotations

from fastapi import APIRouter, Depends

from application.game_config.game_config_models import BlindtestBuzzerCommandModel, GameConfigReadModel
from presentation.dependencies import GameConfigCommandDep, HardwareAuthDep

router = APIRouter(prefix="/api/hardware", tags=["hardware"])


@router.post("/buzzer-events", response_model=GameConfigReadModel, summary="Recevoir un buzz matériel USB")
async def receive_hardware_buzzer_event(
    payload: BlindtestBuzzerCommandModel,
    _: HardwareAuthDep,
    command_usecase: GameConfigCommandDep,
) -> GameConfigReadModel:
    return await command_usecase.register_blindtest_buzzer(payload)

