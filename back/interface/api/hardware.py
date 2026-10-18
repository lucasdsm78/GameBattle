from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from application.commands import HARDWARE_BUZZER
from application.commands.payloads import TeamCommand
from application.services.snapshot import ClientRole
from interface.dependencies import (
    CommandBusDep,
    QueryServiceDep,
    require_hardware_token,
)
from interface.schemas.game_config import GameConfigResponse

router = APIRouter(prefix="/api/hardware", tags=["hardware"], dependencies=[Depends(require_hardware_token)])


@router.post("/buzzer-events", response_model=GameConfigResponse, summary="Recevoir un buzz matériel USB")
async def receive_hardware_buzzer_event(payload: TeamCommand, bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    snapshot = await bus.execute(HARDWARE_BUZZER, payload, ClientRole.HARDWARE) or await query.get_current()
    return snapshot.controller
