from __future__ import annotations

from fastapi import APIRouter

from application.game_config.game_config_models import BlindtestBuzzerCommandModel, GameConfigReadModel
from presentation.dependencies import GameConfigCommandDep, HardwareAuthDep, WebSocketHubDep
from presentation.realtime.game_config_ws_handler import build_broadcast_envelopes

router = APIRouter(prefix="/api/hardware", tags=["hardware"])


@router.post("/buzzer-events", response_model=GameConfigReadModel, summary="Recevoir un buzz matériel USB")
async def receive_hardware_buzzer_event(
    payload: BlindtestBuzzerCommandModel,
    _: HardwareAuthDep,
    command_usecase: GameConfigCommandDep,
    hub: WebSocketHubDep,
) -> GameConfigReadModel:
    updated = await command_usecase.register_active_game_buzzer(payload)
    await hub.broadcast_json_by_client_type(build_broadcast_envelopes("game.config.updated", updated))
    return updated

