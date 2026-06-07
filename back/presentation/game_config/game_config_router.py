from __future__ import annotations

from fastapi import APIRouter, Depends

from application.game_config.game_config_command_usecase import GameConfigCommandUseCase
from application.game_config.game_config_models import (
    BlindtestAnswerCommandModel,
    BlindtestBuzzerCommandModel,
    BlindtestPlaybackCommandModel,
    BlindtestPlaybackSyncCommandModel,
    BlindtestPlaylistCommandModel,
    GameConfigReadModel,
    GameConfigUpsertModel,
    SpotifyPlaylistImportCommandModel,
)
from application.game_config.game_config_query_usecase import GameConfigQueryUseCase
from dependency_injections import game_config_command_usecase, game_config_query_usecase

router = APIRouter(prefix="/api/game-config", tags=["game-config"])


@router.get("/current", response_model=GameConfigReadModel, summary="Lire la configuration courante")
async def get_current_game_config(
    query_usecase: GameConfigQueryUseCase = Depends(game_config_query_usecase),
) -> GameConfigReadModel:
    return await query_usecase.get_current()


@router.put("/current", response_model=GameConfigReadModel, summary="Remplacer la configuration courante")
async def replace_current_game_config(
    payload: GameConfigUpsertModel,
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.replace_config(payload)


@router.post("/launch", response_model=GameConfigReadModel, summary="Valider et lancer la partie")
async def launch_game(
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.launch_game()


@router.put("/blindtest/playlist", response_model=GameConfigReadModel, summary="Charger la playlist blindtest")
async def load_blindtest_playlist(
    payload: BlindtestPlaylistCommandModel,
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.load_blindtest_playlist(payload)


@router.post(
    "/blindtest/playlist/import-spotify",
    response_model=GameConfigReadModel,
    summary="Importer une playlist blindtest depuis Spotify",
)
async def import_blindtest_playlist_from_spotify(
    payload: SpotifyPlaylistImportCommandModel,
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.import_blindtest_playlist_from_spotify(payload)


@router.post("/blindtest/buzzer", response_model=GameConfigReadModel, summary="Enregistrer un buzzer blindtest")
async def register_blindtest_buzzer(
    payload: BlindtestBuzzerCommandModel,
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.register_blindtest_buzzer(payload)


@router.post("/blindtest/answer", response_model=GameConfigReadModel, summary="Valider une réponse blindtest")
async def answer_blindtest(
    payload: BlindtestAnswerCommandModel,
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.answer_blindtest(payload)


@router.post("/blindtest/playback/control", response_model=GameConfigReadModel, summary="Piloter la lecture blindtest")
async def control_blindtest_playback(
    payload: BlindtestPlaybackCommandModel,
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.control_blindtest_playback(payload)


@router.post("/blindtest/playback/sync", response_model=GameConfigReadModel, summary="Synchroniser la lecture blindtest")
async def sync_blindtest_playback(
    payload: BlindtestPlaybackSyncCommandModel,
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.sync_blindtest_playback(payload)


@router.post("/blindtest/next-track", response_model=GameConfigReadModel, summary="Passer à la musique blindtest suivante")
async def next_blindtest_track(
    command_usecase: GameConfigCommandUseCase = Depends(game_config_command_usecase),
) -> GameConfigReadModel:
    return await command_usecase.next_blindtest_track()


