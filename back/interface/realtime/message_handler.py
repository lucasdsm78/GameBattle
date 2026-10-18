from __future__ import annotations

import logging
import time
from typing import Any, Optional

from pydantic import ValidationError

from application.shared.snapshot import ClientRole
from exceptions import ApplicationError, DomainError
from interface.realtime.dispatcher import RealtimeDispatcher
from interface.schemas.websocket import ClientMessage

logger = logging.getLogger(__name__)

MAX_MESSAGE_CHARS = 64 * 1024


class RateLimiter:
    """Seau à jetons par connexion : absorbe les rafales (boutons volume) sans laisser un client inonder le serveur."""

    def __init__(self, rate_per_second: float = 20.0, burst: int = 40) -> None:
        self._rate = rate_per_second
        self._capacity = float(burst)
        self._tokens = float(burst)
        self._updated_at = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        self._tokens = min(self._capacity, self._tokens + (now - self._updated_at) * self._rate)
        self._updated_at = now
        if self._tokens < 1:
            return False
        self._tokens -= 1
        return True


def error_reply(detail: str) -> dict[str, str]:
    return {"type": "error", "detail": detail}


async def handle_client_message(raw: str, role: ClientRole, dispatcher: RealtimeDispatcher) -> Optional[dict[str, Any]]:
    """Traite un message entrant. Renvoie la réponse directe à l'émetteur, ou `None` (le nouvel état est diffusé à tous)."""
    if len(raw) > MAX_MESSAGE_CHARS:
        return error_reply("Message trop volumineux.")
    try:
        message = ClientMessage.model_validate_json(raw)
    except ValidationError:
        return error_reply("Message JSON invalide.")
    if message.type == "ping":
        return {"type": "pong"}
    try:
        await dispatcher.dispatch(message.type, message.payload, role)
    except (DomainError, ApplicationError) as exc:
        return error_reply(exc.message)
    except Exception:
        logger.exception("game_config.websocket.dispatch_failed", extra={"event_type": message.type})
        return error_reply("Erreur interne lors de la mise à jour.")
    return None
