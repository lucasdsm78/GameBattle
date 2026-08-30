from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from dependency_injections import get_settings
from infrastructure.config import Settings
from infrastructure.http_exception_handlers import register_exception_handlers
from infrastructure.postgresql.database import close_database, configure_database, init_database
from presentation.game_config.game_config_router import router as game_config_router
from presentation.hardware.hardware_buzzer_router import router as hardware_router
from presentation.realtime.game_config_ws_router import router as realtime_router


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self' ws: wss: http: https:; img-src 'self' data:; style-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'",
        )
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        return response


def build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        configure_database(settings)
        await init_database()
        try:
            yield
        finally:
            await close_database()

    return lifespan


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Application factory FastAPI.

    La création de l'app reste compatible avec `uvicorn main:app`, mais les tests peuvent aussi
    instancier une app isolée via `create_app(settings)` sans dupliquer la composition racine.
    """
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        lifespan=build_lifespan(resolved_settings),
        **resolved_settings.fastapi_docs_urls,
    )

    register_exception_handlers(app)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"], summary="Healthcheck")
    async def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "app": resolved_settings.app_name,
            "environment": resolved_settings.environment,
        }

    app.include_router(game_config_router)
    app.include_router(hardware_router)
    app.include_router(realtime_router)
    return app


app = create_app()

