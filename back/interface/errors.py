from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from exceptions import (
    AlreadyInRoomError,
    ApplicationError,
    CommandNotAllowedError,
    ConcurrentModificationError,
    DomainError,
    GameConfigurationNotReadyError,
    InvalidCommandPayloadError,
    InvalidCredentialsError,
    NotAuthenticatedError,
    NotInRoomError,
    PseudoAlreadyTakenError,
    RoomFullError,
    RoomNotFoundError,
    TooManyAttemptsError,
    UnknownCommandError,
)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    GameConfigurationNotReadyError: status.HTTP_409_CONFLICT,
    CommandNotAllowedError: status.HTTP_403_FORBIDDEN,
    UnknownCommandError: status.HTTP_404_NOT_FOUND,
    InvalidCommandPayloadError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    PseudoAlreadyTakenError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    NotAuthenticatedError: status.HTTP_401_UNAUTHORIZED,
    TooManyAttemptsError: status.HTTP_429_TOO_MANY_REQUESTS,
    ConcurrentModificationError: status.HTTP_409_CONFLICT,
    RoomNotFoundError: status.HTTP_404_NOT_FOUND,
    NotInRoomError: status.HTTP_404_NOT_FOUND,
    AlreadyInRoomError: status.HTTP_409_CONFLICT,
    RoomFullError: status.HTTP_409_CONFLICT,
}


async def _handle_expected_error(_: Request, exc: Exception) -> JSONResponse:
    status_code = next(
        (code for error_type, code in _STATUS_BY_ERROR.items() if isinstance(exc, error_type)), status.HTTP_400_BAD_REQUEST
    )
    headers = {"Retry-After": str(exc.retry_after_seconds)} if isinstance(exc, TooManyAttemptsError) else None
    content = {"detail": getattr(exc, "message", str(exc))}
    if field := getattr(exc, "field", ""):
        content["field"] = field
    return JSONResponse(status_code=status_code, content=content, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_expected_error)
    app.add_exception_handler(ApplicationError, _handle_expected_error)
