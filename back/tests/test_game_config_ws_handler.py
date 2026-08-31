from __future__ import annotations

import asyncio

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.model.game_config import build_blindtest_track, build_default_game_config
from presentation.realtime.game_config_ws_handler import build_client_envelope, dispatch_game_config_event


class DummyCommandUseCase:
    def __init__(self) -> None:
        self.spotify_token = ""
        self.calls: list[tuple[str, object]] = []

    async def set_spotify_user_token(self, access_token: str) -> None:
        self.spotify_token = access_token

    async def start_bombe(self):
        self.calls.append(("start", None))
        return "bombe-started"

    async def register_bombe_buzzer(self, payload):
        self.calls.append(("buzzer", payload.team))
        return "bombe-passed"

    async def previous_bombe_team(self):
        self.calls.append(("previous", None))
        return "bombe-previous"

    async def explode_bombe(self):
        self.calls.append(("explode", None))
        return "bombe-exploded"


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


def _culture_read_model(answered: bool = False) -> GameConfigReadModel:
    config = build_default_game_config()
    config.games = [
        type(config.games[0])(game_key="blindtest", label="Blindtest", enabled=False, round_count=0),
        type(config.games[0])(game_key="culture", label="Culture générale", enabled=True, round_count=0),
    ]
    config = config.start_session().start_culture().select_culture_difficulty("facile")
    if answered:
        config = config.register_culture_buzzer(config.settings.teams[0]).answer_culture(True)
    return GameConfigReadModel.from_domain(config)


def _rolling_bombe_read_model(*, revealed: bool) -> GameConfigReadModel:
    config = build_default_game_config()
    for game in config.games:
        game.enabled = game.game_key == "bombe"
    prepared = config.start_session().start_bombe(now_ms=1_000)
    roller = prepared.settings.teams[prepared.session.bombe.roller_team_index or 0]
    rolling = prepared.register_bombe_buzzer(roller, now_ms=1_001)
    if revealed:
        rolling = rolling.begin_bombe_after_roll(rolling.session.bombe.die_reveal_at_ms)
    return GameConfigReadModel.from_domain(rolling)


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


def test_display_envelope_masks_culture_answer_before_validation() -> None:
    envelope = build_client_envelope("game.config.snapshot", _culture_read_model(answered=False), "display")
    question = envelope["payload"]["session"]["culture"]["current_question"]

    assert question["question"]
    assert question["answer"] == "Réponse masquée"
    assert question["explanation"] == ""


def test_display_envelope_reveals_culture_answer_without_explanation() -> None:
    envelope = build_client_envelope("game.config.snapshot", _culture_read_model(answered=True), "display")
    question = envelope["payload"]["session"]["culture"]["current_question"]

    assert question["answer"] != "Réponse masquée"
    assert question["explanation"] == ""


def test_die_result_is_hidden_while_rolling_then_revealed() -> None:
    rolling = build_client_envelope("game.config.updated", _rolling_bombe_read_model(revealed=False), "display")
    running = build_client_envelope("game.config.updated", _rolling_bombe_read_model(revealed=True), "display")

    assert rolling["payload"]["session"]["bombe"]["phase"] == "rolling"
    assert rolling["payload"]["session"]["bombe"]["die_result"] == ""
    assert running["payload"]["session"]["bombe"]["phase"] == "running"
    assert running["payload"]["session"]["bombe"]["die_result"] in {"TIC", "TAC", "BOUM"}


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


def test_display_can_dispatch_bombe_buzzer_and_explosion_only() -> None:
    command_usecase = DummyCommandUseCase()

    buzzer_result = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="bombe.buzzer",
        payload={"team": "Rouges"},
        command_usecase=command_usecase,  # type: ignore[arg-type]
    ))
    explosion_result = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="bombe.explode",
        payload={},
        command_usecase=command_usecase,  # type: ignore[arg-type]
    ))
    forbidden_result = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="bombe.previous-team",
        payload={},
        command_usecase=command_usecase,  # type: ignore[arg-type]
    ))

    assert buzzer_result == "bombe-passed"
    assert explosion_result == "bombe-exploded"
    assert forbidden_result == {"type": "error", "detail": "Le client display est en lecture seule."}
    assert command_usecase.calls == [("buzzer", "Rouges"), ("explode", None)]


def test_controller_can_start_and_go_back_in_bombe() -> None:
    command_usecase = DummyCommandUseCase()

    start_result = asyncio.run(dispatch_game_config_event(
        client_type="controller",
        event_type="bombe.start",
        payload={},
        command_usecase=command_usecase,  # type: ignore[arg-type]
    ))
    previous_result = asyncio.run(dispatch_game_config_event(
        client_type="controller",
        event_type="bombe.previous-team",
        payload={},
        command_usecase=command_usecase,  # type: ignore[arg-type]
    ))

    assert start_result == "bombe-started"
    assert previous_result == "bombe-previous"
    assert command_usecase.calls == [("start", None), ("previous", None)]

