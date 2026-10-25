from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from application.shared.snapshot import ClientRole
from domain.auction.models.auction_state import (
    AUCTION_DURATION_MS,
    AUCTION_MAX_TARGET_COUNT,
    AUCTION_WINNING_SCORE,
)
from domain.game_night.models.game_config import build_default_game_config
from exceptions import (
    CommandNotAllowedError,
    InvalidGameConfigError,
    UnknownCommandError,
)
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from interface.realtime.deadline_worker import GameDeadlineWorker
from support import GameHarness


def _auction_config(*, teams: list[str] | None = None):
    config = build_default_game_config()
    config.settings.teams = teams or ["Rouges", "Bleus", "Verts"]
    config.settings.buzzer_keys = [str(index + 1) for index in range(len(config.settings.teams))]
    config.settings.total_rounds = 1
    for game in config.games:
        game.enabled = game.game_key == "auction"
    return config.start_session()


def _ready_config(target: int = 3, team: str = "Rouges"):
    bidding = _auction_config().start_auction()
    bidding = bidding.register_auction_buzzer(team, now_ms=100)
    return bidding.select_auction_bid(team, target)


def test_start_select_and_launch_prepare_a_server_timed_attempt() -> None:
    bidding = _auction_config().start_auction()
    game = bidding.session.auction
    assert game.phase == "bidding"
    assert game.prompt
    assert len(game.answers) >= 5
    assert game.scores == {"Rouges": 0, "Bleus": 0, "Verts": 0}

    buzzed = bidding.register_auction_buzzer("Bleus", now_ms=100)
    assert buzzed.session.auction.bidding_teams == ["Bleus"]
    assert buzzed.register_auction_buzzer("Bleus", now_ms=101) is buzzed

    ready = buzzed.select_auction_bid("Bleus", 4)
    assert ready.session.auction.phase == "ready"
    assert ready.session.auction.active_team == "Bleus"
    assert ready.session.auction.target_count == 4

    running = ready.launch_auction_attempt(now_ms=50_000)
    assert running.session.auction.phase == "running"
    assert running.session.auction.deadline_at_ms == 50_000 + AUCTION_DURATION_MS


def test_objective_is_independent_from_secret_answer_count_and_bounded_at_one_hundred() -> None:
    bidding = _auction_config().start_auction()
    with pytest.raises(InvalidGameConfigError, match="compris entre"):
        bidding.select_auction_bid("Rouges", 0)

    above_suggestions = min(AUCTION_MAX_TARGET_COUNT, len(bidding.session.auction.answers) + 1)
    selected = bidding.select_auction_bid("Rouges", above_suggestions)
    assert selected.session.auction.target_count == above_suggestions

    with pytest.raises(InvalidGameConfigError, match="compris entre"):
        bidding.select_auction_bid("Rouges", AUCTION_MAX_TARGET_COUNT + 1)


def test_presenter_can_select_a_team_without_a_recorded_buzz() -> None:
    bidding = _auction_config().start_auction()
    selected = bidding.select_auction_bid("Rouges", 2)
    assert selected.session.auction.phase == "ready"
    assert selected.session.auction.active_team == "Rouges"


def test_success_awards_the_bid_to_active_team_when_it_buzzes() -> None:
    current = _ready_config(target=3).launch_auction_attempt(now_ms=1_000)
    for now in (2_000, 3_000, 4_000, 5_000):
        current = current.change_auction_count(1, now_ms=now)
    assert current.session.auction.correct_count == 3

    resolved = current.register_auction_buzzer("Rouges", now_ms=6_000)
    game = resolved.session.auction
    assert game.phase == "resolved"
    assert game.attempt_succeeded is True
    assert game.scores == {"Rouges": 3, "Bleus": 0, "Verts": 0}
    assert game.points_awarded == {"Rouges": 3, "Bleus": 0, "Verts": 0}


def test_failure_awards_two_points_to_every_opponent() -> None:
    running = _ready_config(target=3).launch_auction_attempt(now_ms=1_000)
    running = running.change_auction_count(1, now_ms=2_000)

    with pytest.raises(InvalidGameConfigError, match="Seule l’équipe"):
        running.register_auction_buzzer("Bleus", now_ms=3_000)
    with pytest.raises(InvalidGameConfigError, match="pas encore"):
        running.expire_auction_attempt(now_ms=30_999)

    resolved = running.expire_auction_attempt(now_ms=31_000)
    assert resolved.session.auction.attempt_succeeded is False
    assert resolved.session.auction.scores == {"Rouges": 0, "Bleus": 2, "Verts": 2}
    assert resolved.session.auction.points_awarded == {"Rouges": 0, "Bleus": 2, "Verts": 2}
    assert resolved.expire_auction_attempt(now_ms=40_000) is resolved


def test_next_theme_keeps_scores_and_does_not_repeat_immediately() -> None:
    first = _ready_config(target=1).launch_auction_attempt(now_ms=1_000)
    first = first.change_auction_count(1, now_ms=2_000).register_auction_buzzer("Rouges", now_ms=3_000)
    previous_id = first.session.auction.theme_id

    next_theme = first.next_auction_theme()
    game = next_theme.session.auction
    assert game.phase == "bidding"
    assert game.theme_id != previous_id
    assert game.scores["Rouges"] == 1
    assert game.asked_theme_ids == [previous_id, game.theme_id]


def test_first_team_at_twenty_finishes_the_manche() -> None:
    ready = _ready_config(target=2)
    ready = ready._replace_session(auction=replace(ready.session.auction, scores={"Rouges": 18, "Bleus": 4, "Verts": 2}))
    running = ready.launch_auction_attempt(now_ms=1_000)
    running = running.change_auction_count(1, 2_000).change_auction_count(1, 3_000)
    finished = running.register_auction_buzzer("Rouges", now_ms=4_000)

    assert finished.session.auction.phase == "finished"
    assert finished.session.auction.scores["Rouges"] == AUCTION_WINNING_SCORE
    assert finished.session.auction.winner_team == "Rouges"
    assert finished.session.manche_finished is True
    assert finished.session.manche_winner == "Rouges"
    assert finished.session.active_round and finished.session.active_round.completed


def test_persistence_round_trip_and_display_redaction() -> None:
    started = _auction_config().start_auction()
    restored = game_config_from_payload(game_config_to_payload(started))
    assert restored.session.auction == started.session.auction

    controller, display = present_game_config(started)
    controller_game = controller["session"]["auction"]
    display_game = display["session"]["auction"]
    assert controller_game["answers"]
    assert "asked_theme_ids" not in controller_game
    assert display_game["answers"] == []
    assert "asked_theme_ids" not in display_game


def test_display_can_only_buzz_for_auction() -> None:
    harness = GameHarness(_auction_config().start_auction())

    harness.run("auction.buzzer", {"team": "Rouges"}, role=ClientRole.DISPLAY)
    for forbidden in ("auction.increment", "auction.next-theme"):
        with pytest.raises(CommandNotAllowedError, match="lecture seule"):
            harness.run(forbidden, role=ClientRole.DISPLAY)

    assert harness.config.session.auction.bidding_teams == ["Rouges"]


def test_duplicate_bid_buzz_is_a_no_op_without_write_or_broadcast() -> None:
    harness = GameHarness(_auction_config().start_auction())

    assert harness.run("auction.buzzer", {"team": "Rouges"}) is not None
    assert harness.run("auction.buzzer", {"team": "Rouges"}) is None
    assert harness.repository.saves == 1
    assert len(harness.publisher.snapshots) == 1


def test_due_deadline_resolves_the_attempt_once_then_is_a_no_op() -> None:
    running = _ready_config().launch_auction_attempt(now_ms=1_000)
    assert running.expire_due_deadline(1_000 + AUCTION_DURATION_MS - 1) is running

    resolved = running.expire_due_deadline(1_000 + AUCTION_DURATION_MS)
    assert resolved.session.auction.phase == "resolved"
    assert resolved.expire_due_deadline(1_000 + AUCTION_DURATION_MS + 5_000) is resolved


def test_deadline_worker_expires_and_broadcasts_an_overdue_attempt() -> None:
    clock = {"now": 1_000}
    harness = GameHarness(_ready_config().launch_auction_attempt(now_ms=1_000), now_ms=lambda: clock["now"])
    worker = GameDeadlineWorker(harness.use_cases.game_night)

    assert asyncio.run(worker.check_once()) is False
    clock["now"] = 1_000 + AUCTION_DURATION_MS
    assert asyncio.run(worker.check_once()) is True
    assert asyncio.run(worker.check_once()) is False

    assert harness.config.session.auction.phase == "resolved"
    assert harness.repository.saves == 1
    assert harness.publisher.snapshots[-1].display["session"]["auction"]["answers"] == []


def test_deadline_expiry_is_not_reachable_from_websocket_clients() -> None:
    harness = GameHarness(_ready_config().launch_auction_attempt(now_ms=1_000))

    with pytest.raises(UnknownCommandError):
        harness.run("system.expire-deadlines", role=ClientRole.CONTROLLER)
