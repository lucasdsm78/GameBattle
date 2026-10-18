from __future__ import annotations

import asyncio
import json

import pytest

from application.shared.snapshot import ClientRole
from domain.blindtest.models.blindtest_track import build_blindtest_track
from interface.realtime.message_handler import (
    MAX_MESSAGE_CHARS,
    RateLimiter,
    handle_client_message,
)
from support import GameHarness, started_config

READ_ONLY = {"type": "error", "detail": "Le client display est en lecture seule."}


def _send(harness: GameHarness, message: dict | str, role: ClientRole = ClientRole.CONTROLLER):
    raw = message if isinstance(message, str) else json.dumps(message)
    return asyncio.run(handle_client_message(raw, role, harness.dispatcher))


def _blindtest_config(*, revealed: bool = False):
    config = started_config("blindtest", teams=["Rouges", "Bleus"])
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
    return config.register_buzzer("Rouges").mark_answer(True) if revealed else config


def _culture_config(*, answered: bool = False):
    config = started_config("culture", teams=["Rouges", "Bleus"]).start_culture().select_culture_difficulty("facile")
    return config.register_culture_buzzer("Rouges").answer_culture(True) if answered else config


def _rolling_bombe_config(*, revealed: bool):
    prepared = started_config("bombe", teams=["Rouges", "Bleus"]).start_bombe(now_ms=1_000)
    roller = prepared.settings.teams[prepared.session.bombe.roller_team_index or 0]
    rolling = prepared.register_bombe_buzzer(roller, now_ms=1_001)
    return rolling.begin_bombe_after_roll(rolling.session.bombe.die_reveal_at_ms) if revealed else rolling


def test_display_view_masks_blindtest_answer_before_reveal() -> None:
    controller, display = _blindtest_config(revealed=False).client_views()
    blindtest = display["session"]["blindtest"]

    assert blindtest["current_track"]["track_id"]
    assert blindtest["current_track"]["title"] == "Titre masqué"
    assert blindtest["current_track"]["artist"] == "Artiste masqué"
    assert blindtest["current_track"]["preview_url"] == ""
    assert blindtest["current_track"]["artwork_url"] == ""
    assert blindtest["tracks"] == []
    assert controller["session"]["blindtest"]["current_track"]["title"].startswith("Title ")
    assert "round_sequence" not in controller["session"] and "round_sequence" not in display["session"]


def test_display_view_reveals_blindtest_answer_after_correct_answer() -> None:
    _, display = _blindtest_config(revealed=True).client_views()
    blindtest = display["session"]["blindtest"]

    assert blindtest["current_track"]["title"].startswith("Title ")
    assert blindtest["current_track"]["artist"].startswith("Artist ")
    assert blindtest["current_track"]["artwork_url"].startswith("https://example.com/")
    assert blindtest["tracks"] == []


def test_display_view_masks_culture_answer_before_validation() -> None:
    _, display = _culture_config(answered=False).client_views()
    question = display["session"]["culture"]["current_question"]

    assert question["question"]
    assert question["answer"] == "Réponse masquée"
    assert question["explanation"] == ""


def test_display_view_reveals_culture_answer_without_explanation() -> None:
    _, display = _culture_config(answered=True).client_views()
    question = display["session"]["culture"]["current_question"]

    assert question["answer"] != "Réponse masquée"
    assert question["explanation"] == ""


def test_die_result_is_hidden_from_everyone_while_rolling_then_revealed() -> None:
    rolling_controller, rolling_display = _rolling_bombe_config(revealed=False).client_views()
    _, running_display = _rolling_bombe_config(revealed=True).client_views()

    assert rolling_display["session"]["bombe"]["phase"] == "rolling"
    assert rolling_display["session"]["bombe"]["die_result"] == ""
    assert rolling_controller["session"]["bombe"]["die_result"] == ""
    assert running_display["session"]["bombe"]["phase"] == "running"
    assert running_display["session"]["bombe"]["die_result"] in {"TIC", "TAC", "BOUM"}


def test_display_cannot_dispatch_controller_only_event() -> None:
    harness = GameHarness(started_config("blindtest"))

    assert _send(harness, {"type": "game.config.launch"}, ClientRole.DISPLAY) == READ_ONLY
    assert harness.repository.saves == 0


def test_spotify_user_token_is_stored_without_broadcast() -> None:
    harness = GameHarness(started_config("blindtest"))

    reply = _send(harness, {"type": "spotify.user-token", "payload": {"access_token": "spotify-user-token"}}, ClientRole.DISPLAY)

    assert reply is None
    assert harness.playlists.user_token == "spotify-user-token"
    assert harness.publisher.snapshots == []
    assert harness.repository.saves == 0


def test_display_can_roll_and_explode_but_not_go_back_in_bombe() -> None:
    prepared = started_config("bombe", teams=["Rouges", "Bleus"]).start_bombe(now_ms=1_000)
    harness = GameHarness(prepared, now_ms=2_000)
    roller = prepared.settings.teams[prepared.session.bombe.roller_team_index or 0]

    assert _send(harness, {"type": "bombe.buzzer", "payload": {"team": roller}}, ClientRole.DISPLAY) is None
    assert harness.config.session.bombe.phase == "rolling"
    assert _send(harness, {"type": "bombe.previous-team"}, ClientRole.DISPLAY) == READ_ONLY
    assert len(harness.publisher.snapshots) == 1


def test_controller_commands_are_applied_persisted_and_broadcast() -> None:
    harness = GameHarness(started_config("bombe", teams=["Rouges", "Bleus"]))

    assert _send(harness, {"type": "bombe.start"}) is None

    assert harness.config.session.bombe.phase == "awaiting_roll"
    assert harness.repository.saves == 1
    snapshot = harness.publisher.snapshots[-1]
    assert snapshot.controller["session"]["bombe"]["phase"] == "awaiting_roll"
    assert snapshot.display["session"]["bombe"]["sound"] == harness.config.session.bombe.sound


def test_domain_errors_are_replied_without_persisting() -> None:
    harness = GameHarness(started_config("bombe", teams=["Rouges", "Bleus"]))

    reply = _send(harness, {"type": "bombe.previous-team"})

    assert reply == {"type": "error", "detail": "La Bombe n'est pas en cours."}
    assert harness.repository.saves == 0


@pytest.mark.parametrize(
    ("message", "detail"),
    [
        ("{not json", "Message JSON invalide."),
        (json.dumps({"payload": {}}), "Message JSON invalide."),
        (json.dumps({"type": "DROP TABLE"}), "Message JSON invalide."),
        (json.dumps({"type": "unknown.event"}), "Type d'évènement non supporté."),
        (json.dumps({"type": "bombe.buzzer", "payload": {"team": 42}}), "Données invalides pour « bombe.buzzer » (team)."),
        (json.dumps({"type": "bombe.buzzer", "payload": {"team": "Rouges", "admin": True}}), "Données invalides pour « bombe.buzzer » (admin)."),
        ("x" * (MAX_MESSAGE_CHARS + 1), "Message trop volumineux."),
    ],
)
def test_malformed_messages_are_rejected(message: str, detail: str) -> None:
    harness = GameHarness(started_config("bombe", teams=["Rouges", "Bleus"]))

    assert _send(harness, message) == {"type": "error", "detail": detail}
    assert harness.repository.saves == 0


def test_ping_gets_a_pong() -> None:
    assert _send(GameHarness(started_config("bombe")), {"type": "ping"}) == {"type": "pong"}


def test_rate_limiter_absorbs_a_burst_then_throttles() -> None:
    limiter = RateLimiter(rate_per_second=0.0001, burst=3)

    assert [limiter.allow() for _ in range(4)] == [True, True, True, False]
