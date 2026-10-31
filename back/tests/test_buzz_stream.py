from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from domain.shared.events import BuzzStreamAutoPaused
from domain.shared.models.buzz_stream_state import BUZZ_STREAM_AUTO_PAUSE_AFTER, BUZZ_STREAM_LOCK_MS
from exceptions import InvalidGameConfigError
from support import GameHarness, started_config

TEAMS = ["Rouges", "Bleus"]
START_MS = 1_000
# Calcul flash et Le bon drapeau partagent la même mécanique de défilement.
GAMES = {
    "flash_calc": ("start_flash_calc", "register_flash_calc_buzzer", "pause_flash_calc", "resume_flash_calc"),
    "right_flag": ("start_right_flag", "register_right_flag_buzzer", "pause_right_flag", "resume_right_flag"),
}


def _running(game_key: str):
    start = GAMES[game_key][0]
    return getattr(started_config(game_key, teams=TEAMS).pull_events()[0], start)(START_MS)


def _game(config, game_key: str):
    return config.session.game(game_key)


def _let_items_pass(config, game_key: str, count: int):
    """Laisse passer `count` éléments sans aucun buzz (les retours éventuels s'écoulent aussi)."""
    for _ in range(count):
        while _game(config, game_key).phase == "feedback":
            config = config.expire_due_deadline(_game(config, game_key).deadline_ms)
        config = config.expire_due_deadline(_game(config, game_key).deadline_ms)
    return config


def _buzz(config, game_key: str, team: str = "Rouges", *, late: bool = False):
    game = _game(config, game_key)
    now_ms = game.deadline_ms if late else game.shown_at_ms + BUZZ_STREAM_LOCK_MS
    return getattr(config, GAMES[game_key][1])(team, now_ms)


@pytest.mark.parametrize("game_key", GAMES)
def test_the_scrolling_pauses_itself_when_nobody_plays(game_key: str) -> None:
    almost = _let_items_pass(_running(game_key), game_key, BUZZ_STREAM_AUTO_PAUSE_AFTER - 1)
    assert _game(almost, game_key).phase in {"running", "feedback"}

    paused = _let_items_pass(almost, game_key, 1)
    game = _game(paused, game_key)
    assert game.phase == "paused" and game.auto_paused and game.unanswered_streak == 0
    assert paused.pending_events[-1] == BuzzStreamAutoPaused(game_key, unanswered_items=BUZZ_STREAM_AUTO_PAUSE_AFTER)
    assert paused.expire_due_deadline(10**12) is paused  # plus rien à écrire ni à diffuser


@pytest.mark.parametrize("game_key", GAMES)
def test_any_buzz_restarts_the_count(game_key: str) -> None:
    current = _let_items_pass(_running(game_key), game_key, BUZZ_STREAM_AUTO_PAUSE_AFTER - 1)
    while _game(current, game_key).phase == "feedback":  # un buzz pendant un retour est ignoré, par règle
        current = current.expire_due_deadline(_game(current, game_key).deadline_ms)
    assert _game(_buzz(current, game_key), game_key).unanswered_streak == 0
    assert _game(_buzz(current, game_key, late=True), game_key).unanswered_streak == 0

    later = _let_items_pass(_buzz(current, game_key), game_key, BUZZ_STREAM_AUTO_PAUSE_AFTER - 1)
    assert not _game(later, game_key).auto_paused


@pytest.mark.parametrize("game_key", GAMES)
def test_the_controller_resumes_an_automatic_pause(game_key: str) -> None:
    paused = _let_items_pass(_running(game_key), game_key, BUZZ_STREAM_AUTO_PAUSE_AFTER)
    resumed = _game(getattr(paused, GAMES[game_key][3])(10**9), game_key)

    assert resumed.phase == "running" and not resumed.auto_paused and resumed.shown_at_ms == 10**9
    manual = _game(getattr(_running(game_key), GAMES[game_key][2])(), game_key)
    assert manual.phase == "paused" and not manual.auto_paused


@pytest.mark.parametrize("game_key", GAMES)
def test_clients_see_the_automatic_pause_but_not_the_internal_count(game_key: str) -> None:
    paused = _let_items_pass(_running(game_key), game_key, BUZZ_STREAM_AUTO_PAUSE_AFTER)

    for view in present_game_config(paused):
        payload = view["session"][game_key]
        assert payload["auto_paused"] is True and payload["auto_pause_after"] == BUZZ_STREAM_AUTO_PAUSE_AFTER
        assert "unanswered_streak" not in payload


@pytest.mark.parametrize("game_key", GAMES)
def test_the_deadline_worker_stops_writing_once_paused(game_key: str) -> None:
    almost = _let_items_pass(_running(game_key), game_key, BUZZ_STREAM_AUTO_PAUSE_AFTER - 1)
    while _game(almost, game_key).phase == "feedback":
        almost = almost.expire_due_deadline(_game(almost, game_key).deadline_ms)
    clock = {"now": _game(almost, game_key).deadline_ms}
    harness = GameHarness(almost, now_ms=lambda: clock["now"])

    snapshot = asyncio.run(harness.use_cases.game_night.expire_due_deadlines())
    assert snapshot is not None and [event["type"] for event in snapshot.events] == ["buzz_stream.auto_paused"]

    saves = harness.repository.saves
    clock["now"] += 60_000
    assert asyncio.run(harness.use_cases.game_night.expire_due_deadlines()) is None
    assert harness.repository.saves == saves


@pytest.mark.parametrize("game_key", GAMES)
def test_tampered_automatic_pauses_are_rejected(game_key: str) -> None:
    running = _running(game_key)
    game = _game(running, game_key)

    for tampered in (replace(game, auto_paused=True), replace(game, unanswered_streak=BUZZ_STREAM_AUTO_PAUSE_AFTER)):
        with pytest.raises(InvalidGameConfigError, match="pause automatique"):
            running._replace_session(**{game_key: tampered}).validate()
