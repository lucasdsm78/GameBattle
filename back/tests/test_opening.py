from __future__ import annotations

import asyncio
from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import GAME_PRESENTERS, present_game_config
from application.shared.snapshot import ClientRole
from domain.game_night.events import RulesShown, TeamsPresented
from domain.game_night.models.game_config import (
    RULES_MS,
    TEAM_INTRO_MS,
    TEAMS_OUTRO_MS,
    build_default_game_config,
)
from domain.game_night.models.game_registry import GAME_STATE_TYPES
from exceptions import CommandNotAllowedError, InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from support import GameHarness

TEAMS = ["Rouges", "Bleus", "Verts"]
START_MS = 1_000_000
INTRO_MS = TEAM_INTRO_MS * len(TEAMS) + TEAMS_OUTRO_MS


def _launched(game_key: str = "vanishing_word", *, total_rounds: int = 1):
    config = build_default_game_config()
    config.settings.teams = list(TEAMS)
    config.settings.buzzer_keys = ["1", "2", "3"]
    config.settings.total_rounds = total_rounds
    for game in config.games:
        game.enabled = game.game_key == game_key
    return config.start_session(START_MS)


def _produced(before, after):
    return after.pending_events[len(before.pending_events):]


def test_the_night_opens_on_the_teams_entering_one_after_another() -> None:
    session = _launched().session

    assert session.opening_stage == "teams"
    assert session.opening_started_ms == START_MS and session.opening_until_ms == START_MS + INTRO_MS
    assert _launched().pending_events[-1] == TeamsPresented(tuple(TEAMS))


def test_the_rules_of_the_first_manche_follow_the_teams_then_the_board() -> None:
    launched = _launched()
    assert launched.expire_due_deadline(START_MS + INTRO_MS - 1) is launched

    rules = launched.expire_due_deadline(START_MS + INTRO_MS)
    assert rules.session.opening_stage == "rules"
    assert rules.session.opening_until_ms == START_MS + INTRO_MS + RULES_MS
    assert _produced(launched, rules) == (RulesShown(1, "vanishing_word"),)

    board = rules.expire_due_deadline(START_MS + INTRO_MS + RULES_MS)
    assert board.session.opening_stage == "" and board.session.opening_until_ms == 0


def test_the_controller_can_skip_each_step() -> None:
    rules = _launched().skip_opening(START_MS + 10)
    assert rules.session.opening_stage == "rules" and rules.session.opening_started_ms == START_MS + 10

    board = rules.skip_opening(START_MS + 20)
    assert board.session.opening_stage == ""
    with pytest.raises(InvalidGameConfigError, match="Aucune présentation"):
        board.skip_opening(START_MS + 30)


def test_playing_closes_the_rules_screen() -> None:
    rules = _launched().skip_opening(START_MS)

    playing = rules.start_vanishing_round(START_MS + 1)
    assert playing.session.opening_stage == "" and playing.session.vanishing_word.phase == "memorizing"


def test_each_new_manche_opens_on_its_rules() -> None:
    finished = _launched(total_rounds=2).skip_opening(START_MS).skip_opening(START_MS)
    game = finished.session.vanishing_word
    finished = finished._replace_session(
        vanishing_word=replace(game, phase="finished", winner_team="Rouges", scores={**game.scores, "Rouges": 5}),
        manche_finished=True,
        manche_winner="Rouges",
    )

    second = finished.next_manche(START_MS + 60_000)
    assert second.session.round_index == 1
    assert second.session.opening_stage == "rules" and second.session.opening_until_ms == START_MS + 60_000 + RULES_MS
    assert _produced(finished, second)[-1] == RulesShown(2, "vanishing_word")


def test_clients_receive_the_rules_of_the_active_game_only_during_the_rules() -> None:
    teams_stage = present_game_config(_launched("flash_calc"))[1]["session"]["opening"]
    assert teams_stage["stage"] == "teams" and teams_stage["rules"] is None
    assert teams_stage["team_intro_ms"] == TEAM_INTRO_MS

    controller, display = present_game_config(_launched("flash_calc").skip_opening(START_MS))
    for view in (controller, display):
        opening = view["session"]["opening"]
        assert opening["stage"] == "rules"
        assert opening["rules"]["lines"] == list(GAME_PRESENTERS["flash_calc"].rules.lines)

    board = _launched("flash_calc").skip_opening(START_MS).skip_opening(START_MS)
    assert present_game_config(board)[1]["session"]["opening"] is None


def test_every_game_has_three_lines_of_rules_and_an_example() -> None:
    assert set(GAME_PRESENTERS) == set(GAME_STATE_TYPES)
    for rules in (presenter.rules for presenter in GAME_PRESENTERS.values()):
        assert len(rules.lines) == 3 and all(10 <= len(line) <= 110 for line in rules.lines)
        assert 10 <= len(rules.example) <= 80


def test_the_deadline_worker_moves_the_opening_forward() -> None:
    clock = {"now": START_MS}
    harness = GameHarness(_launched(), now_ms=lambda: clock["now"])

    assert asyncio.run(harness.use_cases.game_night.expire_due_deadlines()) is None
    clock["now"] = START_MS + INTRO_MS
    snapshot = asyncio.run(harness.use_cases.game_night.expire_due_deadlines())
    assert snapshot is not None and [event["type"] for event in snapshot.events] == ["manche.rules_shown"]


def test_only_the_controller_can_skip_and_the_opening_survives_a_reload() -> None:
    harness = GameHarness(_launched(), now_ms=START_MS + 5)
    with pytest.raises(CommandNotAllowedError, match="lecture seule"):
        harness.run("game.skip-opening", role=ClientRole.DISPLAY)
    harness.run("game.skip-opening")
    assert harness.config.session.opening_stage == "rules"

    reloaded = game_config_from_payload(game_config_to_payload(harness.config))
    assert reloaded.session == harness.config.session


def test_tampered_openings_are_rejected() -> None:
    launched = _launched()

    for tampered in ({"opening_stage": "générique"}, {"opening_until_ms": START_MS}):
        with pytest.raises(InvalidGameConfigError, match="ouverture"):
            launched._replace_session(**tampered).validate()
