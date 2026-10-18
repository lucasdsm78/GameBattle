from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from application.game_config.game_config_models import GameConfigReadModel, TeamCommand
from application.game_config.snapshot import ClientRole
from application.games import HARDWARE_BUZZER
from presentation.dependencies import CommandBusDep, QueryServiceDep, require_hardware_token

router = APIRouter(prefix="/api/hardware", tags=["hardware"], dependencies=[Depends(require_hardware_token)])


@router.post("/buzzer-events", response_model=GameConfigReadModel, summary="Recevoir un buzz matériel USB")
async def receive_hardware_buzzer_event(payload: TeamCommand, bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    snapshot = await bus.execute(HARDWARE_BUZZER, payload, ClientRole.HARDWARE) or await query.get_current()
    return snapshot.controller
