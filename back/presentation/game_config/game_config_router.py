from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from application.game_config.game_config_models import (
    AnswerCommand,
    GameConfigReadModel,
    GameConfigUpsertModel,
    PlaybackControlCommand,
    PlaybackSyncCommand,
    PlaylistLoadCommand,
    SpotifyPlaylistImportCommand,
    TeamCommand,
)
from application.game_config.snapshot import ClientRole
from presentation.dependencies import (
    CommandBusDep,
    OptionalControllerToken,
    QueryServiceDep,
    authorize_client,
    require_controller_token,
)

router = APIRouter(prefix="/api/game-config", tags=["game-config"])
commands = APIRouter(dependencies=[Depends(require_controller_token)], responses={401: {"description": "Jeton régie invalide"}})


async def _run(bus: CommandBusDep, query: QueryServiceDep, name: str, payload: BaseModel | None = None) -> dict[str, Any]:
    snapshot = await bus.execute(name, payload, ClientRole.CONTROLLER) or await query.get_current()
    return snapshot.controller


@router.get("/current", response_model=GameConfigReadModel, summary="Lire la configuration courante")
async def get_current_game_config(query: QueryServiceDep, token: OptionalControllerToken = None) -> dict[str, Any]:
    """Vue régie avec le jeton contrôleur, sinon vue écran public (sans aucun secret)."""
    role = ClientRole.CONTROLLER if authorize_client("controller", token) else ClientRole.DISPLAY
    return (await query.get_current()).for_role(role)


@commands.put("/current", response_model=GameConfigReadModel, summary="Remplacer la configuration courante")
async def replace_current_game_config(payload: GameConfigUpsertModel, bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    return await _run(bus, query, "game.config.replace", payload)


@commands.post("/launch", response_model=GameConfigReadModel, summary="Lancer la partie")
async def launch_game(bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    return await _run(bus, query, "game.config.launch")


@commands.put("/blindtest/playlist", response_model=GameConfigReadModel, summary="Charger une playlist blindtest manuelle")
async def load_blindtest_playlist(payload: PlaylistLoadCommand, bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    return await _run(bus, query, "blindtest.playlist.load", payload)


@commands.post(
    "/blindtest/playlist/import-spotify", response_model=GameConfigReadModel, summary="Importer une playlist blindtest Spotify"
)
async def import_blindtest_playlist_from_spotify(
    payload: SpotifyPlaylistImportCommand, bus: CommandBusDep, query: QueryServiceDep
) -> dict[str, Any]:
    return await _run(bus, query, "blindtest.playlist.import-spotify", payload)


@commands.post("/blindtest/buzzer", response_model=GameConfigReadModel, summary="Enregistrer un buzz blindtest")
async def register_blindtest_buzzer(payload: TeamCommand, bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    return await _run(bus, query, "blindtest.buzzer", payload)


@commands.post("/blindtest/answer", response_model=GameConfigReadModel, summary="Valider une réponse blindtest")
async def answer_blindtest(payload: AnswerCommand, bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    return await _run(bus, query, "blindtest.answer", payload)


@commands.post("/blindtest/playback/control", response_model=GameConfigReadModel, summary="Piloter la lecture blindtest")
async def control_blindtest_playback(
    payload: PlaybackControlCommand, bus: CommandBusDep, query: QueryServiceDep
) -> dict[str, Any]:
    return await _run(bus, query, "blindtest.playback.control", payload)


@commands.post("/blindtest/playback/sync", response_model=GameConfigReadModel, summary="Synchroniser la lecture blindtest")
async def sync_blindtest_playback(payload: PlaybackSyncCommand, bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    return await _run(bus, query, "blindtest.playback.sync", payload)


@commands.post("/blindtest/next-track", response_model=GameConfigReadModel, summary="Passer à la musique suivante")
async def next_blindtest_track(bus: CommandBusDep, query: QueryServiceDep) -> dict[str, Any]:
    return await _run(bus, query, "blindtest.next-track")


router.include_router(commands)
