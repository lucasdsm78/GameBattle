from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ValidationError

from application.commands import GameUseCases
from application.services.snapshot import ClientRole
from exceptions import (
    CommandNotAllowedError,
    InvalidCommandPayloadError,
    UnknownCommandError,
)
from interface.realtime.routes import Route

DISPLAY_READ_ONLY_MESSAGE = "Le client display est en lecture seule."


class RealtimeDispatcher:
    """Aiguille un message WebSocket vers son use case : route connue, rôle autorisé, données validées."""

    def __init__(self, use_cases: GameUseCases, routes: Iterable[Route]) -> None:
        self._use_cases = use_cases
        self._routes: dict[str, Route] = {}
        for route in routes:
            if route.event in self._routes:
                raise ValueError(f"Route WebSocket déclarée deux fois : {route.event}")
            self._routes[route.event] = route

    async def dispatch(self, event: str, payload: Mapping[str, Any] | None, role: ClientRole) -> Any:
        route = self._routes.get(event)
        if route is None:
            raise UnknownCommandError("Type d'évènement non supporté.")
        if role not in route.roles:
            raise CommandNotAllowedError(
                DISPLAY_READ_ONLY_MESSAGE if role is ClientRole.DISPLAY else "Commande non autorisée pour ce client."
            )
        return await route.handler(self._use_cases, self._parse(route, payload))

    @staticmethod
    def _parse(route: Route, payload: Mapping[str, Any] | None) -> BaseModel | None:
        if route.payload_model is None:
            return None
        try:
            return route.payload_model.model_validate(payload or {})
        except ValidationError as exc:
            fields = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
            detail = f" ({', '.join(fields)})" if fields else ""
            raise InvalidCommandPayloadError(f"Données invalides pour « {route.event} »{detail}.") from None
