from __future__ import annotations

import logging
from typing import Any

from application.game_config.command import GameConfigCommandUseCase
from application.game_config.game_config_models import (
    BlindtestAnswerCommandModel,
    BlindtestBuzzerCommandModel,
    BlindtestPlaybackCommandModel,
    BlindtestPlaybackSyncCommandModel,
    BlindtestPlaylistCommandModel,
    CultureDifficultyCommandModel,
    GameConfigEnvelope,
    GameConfigReadModel,
    GameConfigUpsertModel,
    SpotifyPlaylistImportCommandModel,
)
from domain.game_config.exception.game_config_exception import GameConfigurationNotReadyError, InvalidGameConfigError

logger = logging.getLogger(__name__)

DISPLAY_ALLOWED_EVENTS = {"blindtest.buzzer", "stopchrono.start", "stopchrono.stop", "culture.buzzer"}


def build_client_envelope(event_type: str, payload: GameConfigReadModel, client_type: str) -> dict[str, Any]:
    """Construit l'enveloppe adaptée au client.

    Le contrôleur reçoit l'état complet. L'écran public reçoit un état redigé pour éviter de
    spoiler la réponse blindtest avant révélation.
    """
    envelope = GameConfigEnvelope(type=event_type, payload=payload).model_dump()
    session = envelope.get("payload", {}).get("session")
    if not isinstance(session, dict):
        return envelope

    session.pop("round_sequence", None)

    culture = session.get("culture")
    if isinstance(culture, dict):
        culture.pop("questions", None)
        current_question = culture.get("current_question")
        if client_type == "display" and isinstance(current_question, dict):
            if not culture.get("answered"):
                current_question["answer"] = "Réponse masquée"
            current_question["explanation"] = ""

    blindtest = session.get("blindtest")
    if client_type == "display" and isinstance(blindtest, dict):
        current_track = blindtest.get("current_track")
        if not blindtest.get("revealed") and isinstance(current_track, dict):
            blindtest["current_track"] = {
                **current_track,
                "title": "Titre masqué",
                "artist": "Artiste masqué",
                "preview_url": "",
                "artwork_url": "",
            }
        blindtest["tracks"] = []

    return envelope


def build_broadcast_envelopes(event_type: str, payload: GameConfigReadModel) -> dict[str, dict[str, Any]]:
    return {
        "controller": build_client_envelope(event_type, payload, "controller"),
        "display": build_client_envelope(event_type, payload, "display"),
    }


async def dispatch_game_config_event(
    *,
    client_type: str,
    event_type: str,
    payload: dict[str, Any],
    command_usecase: GameConfigCommandUseCase,
) -> GameConfigReadModel | dict[str, str] | None:
    """Applique un évènement WebSocket et retourne un snapshot, une réponse courte, ou None.

    - `None` : aucune diffusion/réponse attendue.
    - `dict` : réponse directe au client appelant (`pong`, `error`, etc.).
    - `GameConfigReadModel` : état mis à jour à broadcaster.
    """
    if event_type == "ping":
        return {"type": "pong"}

    if event_type == "spotify.user-token":
        token = str(payload.get("access_token", ""))
        await command_usecase.set_spotify_user_token(token)
        return None

    if client_type != "controller" and event_type not in DISPLAY_ALLOWED_EVENTS:
        return {"type": "error", "detail": "Le client display est en lecture seule."}

    try:
        if event_type == "game.config.replace":
            return await command_usecase.replace_config(GameConfigUpsertModel(**payload))
        if event_type == "game.config.launch":
            return await command_usecase.launch_game()
        if event_type == "blindtest.playlist.load":
            return await command_usecase.load_blindtest_playlist(BlindtestPlaylistCommandModel(**payload))
        if event_type == "blindtest.playlist.import-spotify":
            return await command_usecase.import_blindtest_playlist_from_spotify(SpotifyPlaylistImportCommandModel(**payload))
        if event_type == "blindtest.playlist.reload":
            return await command_usecase.reload_default_playlist()
        if event_type == "blindtest.buzzer":
            return await command_usecase.register_blindtest_buzzer(BlindtestBuzzerCommandModel(**payload))
        if event_type == "blindtest.answer":
            return await command_usecase.answer_blindtest(BlindtestAnswerCommandModel(**payload))
        if event_type == "blindtest.playback.control":
            return await command_usecase.control_blindtest_playback(BlindtestPlaybackCommandModel(**payload))
        if event_type == "blindtest.playback.sync":
            return await command_usecase.sync_blindtest_playback(BlindtestPlaybackSyncCommandModel(**payload))
        if event_type == "blindtest.next-track":
            return await command_usecase.next_blindtest_track()
        if event_type == "stopchrono.start":
            return await command_usecase.start_stopchrono()
        if event_type == "stopchrono.stop":
            return await command_usecase.stop_stopchrono()
        if event_type == "stopchrono.next-team":
            return await command_usecase.next_stopchrono_team()
        if event_type == "culture.start":
            return await command_usecase.start_culture()
        if event_type == "culture.select-difficulty":
            return await command_usecase.select_culture_difficulty(CultureDifficultyCommandModel(**payload))
        if event_type == "culture.buzzer":
            return await command_usecase.register_culture_buzzer(BlindtestBuzzerCommandModel(**payload))
        if event_type == "culture.answer":
            return await command_usecase.answer_culture(BlindtestAnswerCommandModel(**payload))
        if event_type == "culture.next-question":
            return await command_usecase.next_culture_question()
        if event_type == "game.next-manche":
            return await command_usecase.next_manche()
        if event_type == "ranking.reveal-next":
            return await command_usecase.reveal_next_ranking()
        return {"type": "error", "detail": "Type d'évènement non supporté."}
    except (InvalidGameConfigError, GameConfigurationNotReadyError) as exc:
        return {"type": "error", "detail": exc.message}
    except Exception:
        logger.exception("game_config.websocket.dispatch_failed", extra={"event_type": event_type})
        return {"type": "error", "detail": "Erreur interne lors de la mise à jour."}


