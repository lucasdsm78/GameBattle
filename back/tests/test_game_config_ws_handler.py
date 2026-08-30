from __future__ import annotations

import asyncio

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.model.game_config import build_blindtest_track, build_default_game_config
from presentation.realtime.game_config_ws_handler import build_client_envelope, dispatch_game_config_event


class DummyCommandUseCase:
    def __init__(self) -> None:
        self.spotify_token = ""

    async def set_spotify_user_token(self, access_token: str) -> None:
        self.spotify_token = access_token


def _blindtest_read_model(revealed: bool = False) -> GameConfigReadModel:
    config = build_default_game_config().start_session()
    tracks = [
        build_blindtest_track(
            track_id=f"track-{index}",
            title=f"Title {index}",
            artist=f"Artist {index}",
            preview_url=f"https://example.com/{index}.mp3",
            artwork_url=f"https://example.com/{index}.jpg",
        )
        for index in range(1, 11)
    ]
    config = config.with_blindtest_tracks(tracks)
    if revealed:
        config = config.register_buzzer(config.settings.teams[0]).mark_answer(True)
    return GameConfigReadModel.from_domain(config)


def test_display_envelope_masks_blindtest_answer_before_reveal() -> None:
    envelope = build_client_envelope("game.config.snapshot", _blindtest_read_model(revealed=False), "display")
    blindtest = envelope["payload"]["session"]["blindtest"]

    assert blindtest["current_track"]["track_id"]
    assert blindtest["current_track"]["title"] == "Titre masqué"
    assert blindtest["current_track"]["artist"] == "Artiste masqué"
    assert blindtest["current_track"]["preview_url"] == ""
    assert blindtest["current_track"]["artwork_url"] == ""
    assert blindtest["tracks"] == []
    assert "round_sequence" not in envelope["payload"]["session"]


def test_display_envelope_reveals_blindtest_answer_after_correct_answer() -> None:
    envelope = build_client_envelope("game.config.snapshot", _blindtest_read_model(revealed=True), "display")
    blindtest = envelope["payload"]["session"]["blindtest"]

    assert blindtest["current_track"]["title"].startswith("Title ")
    assert blindtest["current_track"]["artist"].startswith("Artist ")
    assert blindtest["current_track"]["artwork_url"].startswith("https://example.com/")
    assert blindtest["tracks"] == []


def test_display_cannot_dispatch_controller_only_event() -> None:
    result = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="game.config.launch",
        payload={},
        command_usecase=DummyCommandUseCase(),  # type: ignore[arg-type]
    ))

    assert result == {"type": "error", "detail": "Le client display est en lecture seule."}


def test_spotify_user_token_event_is_not_broadcast() -> None:
    command_usecase = DummyCommandUseCase()

    result = asyncio.run(dispatch_game_config_event(
        client_type="controller",
        event_type="spotify.user-token",
        payload={"access_token": "spotify-user-token"},
        command_usecase=command_usecase,  # type: ignore[arg-type]
    ))

    assert result is None
    assert command_usecase.spotify_token == "spotify-user-token"


