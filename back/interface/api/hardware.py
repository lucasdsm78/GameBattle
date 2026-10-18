from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from application.commands.payloads import TeamCommand
from interface.api.game_config import controller_view
from interface.dependencies import (
    QueryServiceDep,
    SessionUseCaseDep,
    require_hardware_token,
)
from interface.schemas.game_config import GameConfigResponse

router = APIRouter(prefix="/api/hardware", tags=["hardware"], dependencies=[Depends(require_hardware_token)])


@router.post("/buzzer-events", response_model=GameConfigResponse, summary="Recevoir un buzz matériel USB")
async def receive_hardware_buzzer_event(payload: TeamCommand, session: SessionUseCaseDep, query: QueryServiceDep) -> dict[str, Any]:
    return await controller_view(await session.register_hardware_buzzer(payload), query)
