from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from application.game_config.errors import (
    ApplicationError,
    CommandNotAllowedError,
    InvalidCommandPayloadError,
    UnknownCommandError,
)
from domain.game_config.exception.game_config_exception import GameConfigError, GameConfigurationNotReadyError

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    GameConfigurationNotReadyError: status.HTTP_409_CONFLICT,
    CommandNotAllowedError: status.HTTP_403_FORBIDDEN,
    UnknownCommandError: status.HTTP_404_NOT_FOUND,
    InvalidCommandPayloadError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


async def _handle_expected_error(_: Request, exc: Exception) -> JSONResponse:
    status_code = next(
        (code for error_type, code in _STATUS_BY_ERROR.items() if isinstance(exc, error_type)), status.HTTP_400_BAD_REQUEST
    )
    return JSONResponse(status_code=status_code, content={"detail": getattr(exc, "message", str(exc))})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(GameConfigError, _handle_expected_error)
    app.add_exception_handler(ApplicationError, _handle_expected_error)
