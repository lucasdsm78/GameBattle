from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
    (
        b"content-security-policy",
        b"default-src 'self'; connect-src 'self' ws: wss: http: https:; img-src 'self' data:; "
        b"style-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'",
    ),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"cross-origin-resource-policy", b"same-site"),
    (b"cache-control", b"no-store"),
)


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
