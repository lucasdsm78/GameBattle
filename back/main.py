from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.config import Settings
from infrastructure.logging_filters import install_secret_redaction
from interface.api.game_config import router as game_config_router
from interface.api.hardware import router as hardware_router
from interface.api.realtime import router as realtime_router
from interface.dependencies.container import (
    database,
    game_config_repository,
    game_deadline_worker,
    get_settings,
    spotify_playlist_service,
)
from interface.errors import register_exception_handlers
from interface.security import SecurityHeadersMiddleware


def build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        await database().create_schema()
        game_config_repository().clear()
        deadline_worker = game_deadline_worker()
        await deadline_worker.start()
        try:
            yield
        finally:
            await deadline_worker.stop()
            await spotify_playlist_service().aclose()
            await database().dispose()

    return lifespan


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Application factory : `uvicorn main:app` en production, `create_app(settings)` pour une app isolée."""
    resolved_settings = settings or get_settings()
    install_secret_redaction("uvicorn.error", "uvicorn.access")
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
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "X-GameBattle-Controller-Token", "X-GameBattle-Hardware-Token"],
    )

    @app.get("/health", tags=["system"], summary="Healthcheck")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "app": resolved_settings.app_name, "environment": resolved_settings.environment}

    app.include_router(game_config_router)
    app.include_router(hardware_router)
    app.include_router(realtime_router)
    return app


app = create_app()
