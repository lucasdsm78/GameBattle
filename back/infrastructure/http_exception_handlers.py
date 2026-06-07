from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.game_config.exception.game_config_exception import GameConfigurationNotReadyError, InvalidGameConfigError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidGameConfigError)
    async def invalid_game_config_handler(_: Request, exc: InvalidGameConfigError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": exc.message})

    @app.exception_handler(GameConfigurationNotReadyError)
    async def invalid_game_launch_handler(_: Request, exc: GameConfigurationNotReadyError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})

