from __future__ import annotations

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import AUCTION_DURATION_MS, AUCTION_WINNING_SCORE, build_default_game_config
from infrastructure.game_config_payload_mapper import game_config_from_payload
from presentation.realtime.game_config_ws_handler import build_client_envelope, dispatch_game_config_event
from presentation.realtime.auction_deadline_worker import AuctionDeadlineWorker


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


def test_objective_is_bounded_by_secret_answer_count() -> None:
    bidding = _auction_config().start_auction().register_auction_buzzer("Rouges", now_ms=100)
    with pytest.raises(InvalidGameConfigError, match="compris entre"):
        bidding.select_auction_bid("Rouges", 0)
    with pytest.raises(InvalidGameConfigError, match="compris entre"):
        bidding.select_auction_bid("Rouges", len(bidding.session.auction.answers) + 1)


def test_only_a_team_that_buzzed_can_receive_the_bid() -> None:
    bidding = _auction_config().start_auction()
    with pytest.raises(InvalidGameConfigError, match="doit avoir buzzé"):
        bidding.select_auction_bid("Rouges", 2)


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
    restored = game_config_from_payload(started.to_dict())
    assert restored.session.auction == started.session.auction

    model = GameConfigReadModel.from_domain(started)
    controller = build_client_envelope("game.config.updated", model, "controller")
    display = build_client_envelope("game.config.updated", model, "display")
    controller_game = controller["payload"]["session"]["auction"]
    display_game = display["payload"]["session"]["auction"]
    assert controller_game["answers"]
    assert "asked_theme_ids" not in controller_game
    assert display_game["answers"] == []
    assert "asked_theme_ids" not in display_game


class _DisplayCommands:
    async def register_auction_buzzer(self, payload):
        return f"buzz:{payload.team}"

    async def increment_auction_count(self):
        return "incremented"


def test_display_can_only_buzz_for_auction() -> None:
    commands = _DisplayCommands()
    buzzed = asyncio.run(dispatch_game_config_event(
        client_type="display", event_type="auction.buzzer", payload={"team": "Rouges"}, command_usecase=commands  # type: ignore[arg-type]
    ))
    forbidden_expiration = asyncio.run(dispatch_game_config_event(
        client_type="display", event_type="auction.expire", payload={}, command_usecase=commands  # type: ignore[arg-type]
    ))
    forbidden = asyncio.run(dispatch_game_config_event(
        client_type="display", event_type="auction.increment", payload={}, command_usecase=commands  # type: ignore[arg-type]
    ))
    assert buzzed == "buzz:Rouges"
    assert forbidden_expiration == {"type": "error", "detail": "Le client display est en lecture seule."}
    assert forbidden == {"type": "error", "detail": "Le client display est en lecture seule."}


def test_deadline_worker_expires_and_broadcasts_an_overdue_attempt() -> None:
    running = _ready_config().launch_auction_attempt(now_ms=1_000)
    resolved = GameConfigReadModel.from_domain(running.expire_auction_attempt(now_ms=31_000))
    commands = AsyncMock()
    commands.expire_auction_attempt.return_value = resolved
    hub = AsyncMock()
    worker = AuctionDeadlineWorker(commands, hub)  # type: ignore[arg-type]

    assert asyncio.run(worker.check_once()) is True
    commands.expire_auction_attempt.assert_awaited_once()
    hub.broadcast_json_by_client_type.assert_awaited_once()
    envelopes = hub.broadcast_json_by_client_type.await_args.args[0]
    assert envelopes["display"]["payload"]["session"]["auction"]["answers"] == []


def test_deadline_worker_ignores_an_attempt_before_its_deadline() -> None:
    commands = AsyncMock()
    commands.expire_auction_attempt.side_effect = InvalidGameConfigError("Les 30 secondes ne sont pas encore écoulées.")
    hub = AsyncMock()
    worker = AuctionDeadlineWorker(commands, hub)  # type: ignore[arg-type]

    assert asyncio.run(worker.check_once()) is False
    commands.expire_auction_attempt.assert_awaited_once()
    hub.broadcast_json_by_client_type.assert_not_awaited()

