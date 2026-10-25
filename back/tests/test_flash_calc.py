from __future__ import annotations

import asyncio
import random
from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from application.shared.commands import TeamCommand
from application.shared.snapshot import ClientRole
from domain.flash_calc.events import CalculationShown, FlashCalcLevelReached
from domain.flash_calc.services.flash_calc_generator import (
    CALCS_PER_LEVEL,
    FLASH_CALC_LEVELS,
    MAX_LEVEL,
    display_ms_for,
    generate_calculation,
    level_for,
)
from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.models.buzz_stream_state import (
    BUZZ_STREAM_FEEDBACK_MS,
    BUZZ_STREAM_LOCK_MS,
    BUZZ_STREAM_WINNING_SCORE,
)
from exceptions import CommandNotAllowedError, InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from support import GameHarness, started_config

TEAMS = ["Rouges", "Bleus", "Verts"]
START_MS = 1_000
BUZZ_MS = START_MS + BUZZ_STREAM_LOCK_MS


def _running(teams: list[str] | None = None):
    return started_config("flash_calc", teams=teams or TEAMS).pull_events()[0].start_flash_calc(START_MS)


def _rigged(config, *, correct: bool):
    """Force le calcul affiché à être juste ou faux, quel que soit le tirage."""
    game = config.session.flash_calc
    shown = game.true_result if correct else game.true_result + 1
    return config._replace_session(flash_calc=replace(game, shown_result=shown))


def _produced(before, after):
    return after.pending_events[len(before.pending_events):]


def test_starting_shows_a_first_level_one_calculation() -> None:
    game = _running().session.flash_calc

    assert game.phase == "running"
    assert game.calc_number == 1 and game.level == 1
    assert game.expression and game.shown_result >= 0
    assert game.deadline_ms == START_MS + display_ms_for(1)
    assert game.scores == {team: 0 for team in TEAMS}

    with pytest.raises(InvalidGameConfigError, match="déjà commencé"):
        _running().start_flash_calc(START_MS + 1)


def test_an_unanswered_calculation_scrolls_to_the_next_one() -> None:
    running = _running()
    deadline = running.session.flash_calc.deadline_ms

    assert running.expire_due_deadline(deadline - 1) is running
    following = running.expire_due_deadline(deadline).session.flash_calc
    assert following.phase == "running"
    assert following.calc_number == 2
    assert following.expression != running.session.flash_calc.expression
    assert following.scores == running.session.flash_calc.scores


def test_buzzing_a_correct_calculation_scores_one_point() -> None:
    buzzed = _rigged(_running(), correct=True).register_flash_calc_buzzer("Bleus", now_ms=BUZZ_MS)
    game = buzzed.session.flash_calc

    assert game.phase == "feedback"
    assert game.scores == {"Rouges": 0, "Bleus": 1, "Verts": 0}
    assert game.verdict.team == "Bleus" and game.verdict.correct and game.verdict.points == 1
    assert game.deadline_ms == BUZZ_MS + BUZZ_STREAM_FEEDBACK_MS


def test_buzzing_a_wrong_calculation_costs_a_point_but_never_goes_below_zero() -> None:
    scored = _rigged(_running(), correct=True).register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS)
    next_calc = scored.expire_due_deadline(BUZZ_MS + BUZZ_STREAM_FEEDBACK_MS)
    shown_at = next_calc.session.flash_calc.shown_at_ms

    penalised = _rigged(next_calc, correct=False).register_flash_calc_buzzer("Rouges", now_ms=shown_at + BUZZ_STREAM_LOCK_MS)
    assert penalised.session.flash_calc.scores["Rouges"] == 0
    assert penalised.session.flash_calc.verdict.points == -1

    floored = _rigged(_running(), correct=False).register_flash_calc_buzzer("Verts", now_ms=BUZZ_MS).session.flash_calc
    assert floored.scores["Verts"] == 0
    assert floored.verdict.correct is False and floored.verdict.points == 0
    assert floored.verdict.true_result != floored.verdict.shown_result


def test_after_a_buzz_the_feedback_ends_on_a_new_calculation() -> None:
    feedback = _rigged(_running(), correct=False).register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS)
    first = feedback.session.flash_calc

    assert feedback.register_flash_calc_buzzer("Bleus", now_ms=BUZZ_MS + 10) is feedback
    resumed = feedback.expire_due_deadline(first.deadline_ms).session.flash_calc
    assert resumed.phase == "running"
    assert resumed.calc_number == first.calc_number + 1
    assert resumed.expression != first.expression
    assert resumed.verdict is None


def test_buzzes_are_ignored_right_after_a_calculation_appears() -> None:
    running = _running()

    assert running.register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS - 1) is running


def test_a_buzz_after_the_deadline_only_scrolls_to_the_next_calculation() -> None:
    running = _rigged(_running(), correct=True)
    late = running.register_flash_calc_buzzer("Rouges", now_ms=running.session.flash_calc.deadline_ms).session.flash_calc

    assert late.phase == "running" and late.calc_number == 2
    assert late.scores["Rouges"] == 0


def test_buzzers_are_closed_outside_the_scrolling() -> None:
    idle = started_config("flash_calc", teams=TEAMS)
    with pytest.raises(InvalidGameConfigError, match="pas en cours"):
        idle.register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS)
    with pytest.raises(InvalidGameConfigError, match="inconnue"):
        _running().register_flash_calc_buzzer("Jaunes", now_ms=BUZZ_MS)


def test_pause_freezes_the_scrolling_and_resume_shows_a_new_calculation() -> None:
    paused = _running().pause_flash_calc()
    game = paused.session.flash_calc

    assert game.phase == "paused"
    assert paused.expire_due_deadline(10_000_000) is paused
    with pytest.raises(InvalidGameConfigError, match="pause"):
        paused.register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS)

    resumed = paused.resume_flash_calc(50_000).session.flash_calc
    assert resumed.phase == "running"
    assert resumed.calc_number == game.calc_number + 1
    assert resumed.deadline_ms == 50_000 + display_ms_for(resumed.level)
    with pytest.raises(InvalidGameConfigError, match="pas en pause"):
        paused.resume_flash_calc(50_000).resume_flash_calc(50_001)


def test_calculations_speed_up_level_after_level() -> None:
    assert [level_for(number) for number in (1, CALCS_PER_LEVEL, CALCS_PER_LEVEL + 1)] == [1, 1, 2]
    assert level_for(10_000) == MAX_LEVEL
    durations = [level.display_ms for level in FLASH_CALC_LEVELS]
    assert durations == sorted(durations, reverse=True) and durations[-1] >= 2_000


def test_the_first_team_to_reach_the_winning_score_wins_the_manche() -> None:
    current = _running()
    for _ in range(BUZZ_STREAM_WINNING_SCORE):
        shown_at = current.session.flash_calc.shown_at_ms
        current = _rigged(current, correct=True).register_flash_calc_buzzer("Verts", now_ms=shown_at + BUZZ_STREAM_LOCK_MS)
        if current.session.flash_calc.phase == "feedback":
            current = current.expire_due_deadline(current.session.flash_calc.deadline_ms)

    game = current.session.flash_calc
    assert game.phase == "finished"
    assert game.winner_team == "Verts"
    assert game.scores["Verts"] == BUZZ_STREAM_WINNING_SCORE
    assert current.session.manche_winner == "Verts"
    assert current.expire_due_deadline(10_000_000) is current


def test_nobody_ever_sees_whether_the_current_calculation_is_correct() -> None:
    running = _running()
    controller, display = present_game_config(running)

    for view in (controller, display):
        payload = view["session"]["flash_calc"]
        assert "true_result" not in payload
        assert payload["expression"] == running.session.flash_calc.expression
        assert payload["level"] == 1 and payload["winning_score"] == BUZZ_STREAM_WINNING_SCORE


def test_domain_events_follow_the_scrolling() -> None:
    ready = started_config("flash_calc", teams=TEAMS).pull_events()[0]
    running = _rigged(ready.start_flash_calc(START_MS), correct=False)
    buzzed = running.register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS)

    assert _produced(ready, running) == (CalculationShown(1, 1),)
    assert _produced(running, buzzed) == (
        BuzzerPressed("flash_calc", "Rouges"),
        AnswerJudged("flash_calc", "Rouges", correct=False),
    )

    current = buzzed
    for _ in range(CALCS_PER_LEVEL):
        before = current
        current = current.expire_due_deadline(current.session.flash_calc.deadline_ms)
    assert _produced(before, current) == (FlashCalcLevelReached(2), CalculationShown(CALCS_PER_LEVEL + 1, 2))


def test_persistence_round_trip() -> None:
    buzzed = _rigged(_running(), correct=True).register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS)

    assert game_config_from_payload(game_config_to_payload(buzzed)).session.flash_calc == buzzed.session.flash_calc


def test_tampered_states_are_rejected() -> None:
    buzzed = _rigged(_running(), correct=True).register_flash_calc_buzzer("Rouges", now_ms=BUZZ_MS)
    game = buzzed.session.flash_calc

    for tampered, message in (
        (replace(game, scores={**game.scores, "Rouges": -1}), "scores"),
        (replace(game, phase="finished", winner_team="Rouges"), f"{BUZZ_STREAM_WINNING_SCORE} points"),
        (replace(game, verdict=None), "dernier buzz"),
        (replace(game, deadline_ms=0), "chrono"),
        (replace(game, phase="joker"), "phase"),
    ):
        with pytest.raises(InvalidGameConfigError, match=message):
            buzzed._replace_session(flash_calc=tampered).validate()


def test_display_buzzes_through_websocket_but_cannot_pause() -> None:
    harness = GameHarness(_rigged(_running(), correct=True), now_ms=BUZZ_MS)

    snapshot = harness.run("flash-calc.buzzer", {"team": "Bleus"}, role=ClientRole.DISPLAY)
    assert harness.config.session.flash_calc.scores["Bleus"] == 1
    assert [event["type"] for event in snapshot.events] == ["buzzer.pressed", "answer.judged"]
    with pytest.raises(CommandNotAllowedError, match="lecture seule"):
        harness.run("flash-calc.pause", role=ClientRole.DISPLAY)


def test_the_deadline_worker_scrolls_the_calculations() -> None:
    clock = {"now": START_MS}
    harness = GameHarness(_running(), now_ms=lambda: clock["now"])

    assert asyncio.run(harness.use_cases.game_night.expire_due_deadlines()) is None
    clock["now"] = START_MS + display_ms_for(1)
    snapshot = asyncio.run(harness.use_cases.game_night.expire_due_deadlines())

    assert snapshot is not None
    assert snapshot.display["session"]["flash_calc"]["calc_number"] == 2
    assert [event["type"] for event in snapshot.events] == ["flash_calc.calculation_shown"]


def test_a_hardware_buzzer_answers_the_current_calculation() -> None:
    harness = GameHarness(_rigged(_running(), correct=False), now_ms=BUZZ_MS)

    asyncio.run(harness.use_cases.game_night.register_hardware_buzzer(TeamCommand(team="Verts")))

    assert harness.config.session.flash_calc.verdict.team == "Verts"


@pytest.mark.parametrize("level", range(1, MAX_LEVEL + 1))
def test_generated_calculations_stay_mental_and_traps_stay_credible(level: int) -> None:
    rng = random.Random(level)
    calculations = [generate_calculation(level, rng=rng) for _ in range(500)]
    correct = [calculation for calculation in calculations if calculation.is_correct]

    assert 0.3 < len(correct) / len(calculations) < 0.6
    for calculation in calculations:
        assert 0 <= calculation.true_result <= 250 and calculation.shown_result >= 0
        gap = abs(calculation.shown_result - calculation.true_result)
        assert gap <= 25 or str(calculation.shown_result) == str(calculation.true_result)[::-1]
        assert len(calculation.expression) <= 9


def test_two_consecutive_calculations_are_never_identical() -> None:
    rng = random.Random(7)
    previous = ""
    for _ in range(300):
        calculation = generate_calculation(1, avoid=previous, rng=rng)
        assert calculation.expression != previous
        previous = calculation.expression
