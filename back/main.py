from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.config import Settings
from infrastructure.database.schema_version import ensure_schema_is_current
from infrastructure.logging_filters import install_secret_redaction
from interface.api.accounts import router as accounts_router
from interface.api.game_config import router as game_config_router
from interface.api.hardware import router as hardware_router
from interface.api.media import router as media_router
from interface.api.realtime import router as realtime_router
from interface.api.room_realtime import router as room_realtime_router
from interface.api.rooms import router as rooms_router
from interface.client_address import came_through_trusted_proxy
from interface.dependencies.container import (
    account_janitor,
    database,
    game_config_repository,
    game_deadline_worker,
    get_settings,
    outbox_relay,
    room_janitor,
    single_instance_lock,
    spotify_playlist_service,
)
from interface.errors import register_exception_handlers
from interface.security import SecurityHeadersMiddleware


def build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        await single_instance_lock().acquire()  # avant tout : une seconde instance s'arrête ici
        await ensure_schema_is_current(database())  # base en retard sur le code : on s'arrête avec la commande à lancer
        if settings.creates_schema_on_startup:
            await database().create_schema()
        game_config_repository().clear()
        workers = (game_deadline_worker(), account_janitor(), outbox_relay(), room_janitor())
        for worker in workers:
            await worker.start()
        try:
            yield
        finally:
            for worker in workers:
                await worker.stop()
            await single_instance_lock().release()
            await spotify_playlist_service().aclose()
            await database().dispose()

    return lifespan


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Application factory : `uvicorn main:app` en production, `create_app(settings)` pour une app isolée."""
    resolved_settings = settings or get_settings()
    # Journaux de l'application (tâches de fond, avertissements de sécurité) au même format que ceux d'uvicorn.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:     [%(name)s] %(message)s")
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
    async def health_check(request: Request) -> dict[str, str | bool]:
        # `via_trusted_proxy` : le contrôle de santé de Caddy vérifie ainsi que le backend le reconnaît comme proxy.
        return {
            "status": "ok",
            "app": resolved_settings.app_name,
            "environment": resolved_settings.environment,
            "via_trusted_proxy": came_through_trusted_proxy(request),
        }

    app.include_router(game_config_router)
    app.include_router(hardware_router)
    app.include_router(realtime_router)
    app.include_router(media_router)
    app.include_router(accounts_router)
    app.include_router(rooms_router)
    app.include_router(room_realtime_router)
    return app


app = create_app()
