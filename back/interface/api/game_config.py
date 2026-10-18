from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from application.commands.payloads import (
    AnswerCommand,
    GameConfigUpsertModel,
    PlaybackControlCommand,
    PlaybackSyncCommand,
    PlaylistLoadCommand,
    SpotifyPlaylistImportCommand,
    TeamCommand,
)
from application.queries.game_config import GameConfigQueryService
from application.services.snapshot import ClientRole, GameConfigSnapshot
from interface.dependencies import (
    BlindtestUseCaseDep,
    OptionalControllerToken,
    QueryServiceDep,
    SessionUseCaseDep,
    authorize_client,
    require_controller_token,
)
from interface.schemas.game_config import GameConfigResponse

router = APIRouter(prefix="/api/game-config", tags=["game-config"])
commands = APIRouter(dependencies=[Depends(require_controller_token)], responses={401: {"description": "Jeton régie invalide"}})


async def controller_view(snapshot: GameConfigSnapshot | None, query: GameConfigQueryService) -> dict[str, Any]:
    """Vue régie du nouvel état, ou de l'état courant si la commande n'a rien changé."""
    return (snapshot or await query.get_current()).controller


@router.get("/current", response_model=GameConfigResponse, summary="Lire la configuration courante")
async def get_current_game_config(query: QueryServiceDep, token: OptionalControllerToken = None) -> dict[str, Any]:
    """Vue régie avec le jeton contrôleur, sinon vue écran public (sans aucun secret)."""
    role = ClientRole.CONTROLLER if authorize_client("controller", token) else ClientRole.DISPLAY
    return (await query.get_current()).for_role(role)


@commands.put("/current", response_model=GameConfigResponse, summary="Remplacer la configuration courante")
async def replace_current_game_config(
    payload: GameConfigUpsertModel, session: SessionUseCaseDep, query: QueryServiceDep
) -> dict[str, Any]:
    return await controller_view(await session.replace_config(payload), query)


@commands.post("/launch", response_model=GameConfigResponse, summary="Lancer la partie")
async def launch_game(session: SessionUseCaseDep, query: QueryServiceDep) -> dict[str, Any]:
    return await controller_view(await session.launch_game(), query)


@commands.put("/blindtest/playlist", response_model=GameConfigResponse, summary="Charger une playlist blindtest manuelle")
async def load_blindtest_playlist(
    payload: PlaylistLoadCommand, blindtest: BlindtestUseCaseDep, query: QueryServiceDep
) -> dict[str, Any]:
    return await controller_view(await blindtest.load_playlist(payload), query)


@commands.post(
    "/blindtest/playlist/import-spotify", response_model=GameConfigResponse, summary="Importer une playlist blindtest Spotify"
)
async def import_blindtest_playlist_from_spotify(
    payload: SpotifyPlaylistImportCommand, blindtest: BlindtestUseCaseDep, query: QueryServiceDep
) -> dict[str, Any]:
    return await controller_view(await blindtest.import_spotify_playlist(payload), query)


@commands.post("/blindtest/buzzer", response_model=GameConfigResponse, summary="Enregistrer un buzz blindtest")
async def register_blindtest_buzzer(payload: TeamCommand, blindtest: BlindtestUseCaseDep, query: QueryServiceDep) -> dict[str, Any]:
    return await controller_view(await blindtest.register_buzzer(payload), query)


@commands.post("/blindtest/answer", response_model=GameConfigResponse, summary="Valider une réponse blindtest")
async def answer_blindtest(payload: AnswerCommand, blindtest: BlindtestUseCaseDep, query: QueryServiceDep) -> dict[str, Any]:
    return await controller_view(await blindtest.answer(payload), query)


@commands.post("/blindtest/playback/control", response_model=GameConfigResponse, summary="Piloter la lecture blindtest")
async def control_blindtest_playback(
    payload: PlaybackControlCommand, blindtest: BlindtestUseCaseDep, query: QueryServiceDep
) -> dict[str, Any]:
    return await controller_view(await blindtest.control_playback(payload), query)


@commands.post("/blindtest/playback/sync", response_model=GameConfigResponse, summary="Synchroniser la lecture blindtest")
async def sync_blindtest_playback(
    payload: PlaybackSyncCommand, blindtest: BlindtestUseCaseDep, query: QueryServiceDep
) -> dict[str, Any]:
    return await controller_view(await blindtest.sync_playback(payload), query)


@commands.post("/blindtest/next-track", response_model=GameConfigResponse, summary="Passer à la musique suivante")
async def next_blindtest_track(blindtest: BlindtestUseCaseDep, query: QueryServiceDep) -> dict[str, Any]:
    return await controller_view(await blindtest.next_track(), query)


router.include_router(commands)
