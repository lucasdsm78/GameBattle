from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from interface.constants.http import SECURITY_HEADERS


class SecurityHeadersMiddleware:
    """Middleware ASGI pur (plus léger que `BaseHTTPMiddleware`) : en-têtes de sécurité sur chaque réponse HTTP.

    `no-store` évite qu'un état de partie contenant les réponses de la régie soit mis en cache.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = {name.lower() for name, _ in message.get("headers", [])}
                message["headers"] = [
                    *message.get("headers", []),
                    *(header for header in SECURITY_HEADERS if header[0] not in existing),
                ]
            await send(message)

        await self.app(scope, receive, send_with_headers)
