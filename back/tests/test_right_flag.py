from __future__ import annotations

import asyncio
import random
import re
from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from application.shared.commands import TeamCommand
from application.shared.snapshot import ClientRole
from domain.right_flag.events import CountryAnnounced, FlagRevealed
from domain.right_flag.models.right_flag_state import flag_display_ms
from domain.right_flag.services.flag_catalog import (
    COUNTRIES,
    COUNTRIES_BY_CODE,
    FLAGS_PER_ROUND,
    LOOKALIKES_PER_ROUND,
    pick_round,
)
from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.shared.models.buzz_stream_state import (
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


def _running(teams: list[str] | None = None):
    return started_config("right_flag", teams=teams or TEAMS).pull_events()[0].start_right_flag(START_MS)


def _game(config):
    return config.session.right_flag


def _scroll_until(config, *, target: bool):
    """Laisse défiler jusqu'au bon drapeau (`target=True`) ou jusqu'à un sosie."""
    while (_game(config).flag_index == _game(config).target_index) != target:
        config = config.expire_due_deadline(_game(config).deadline_ms)
    return config


def _buzz(config, team: str):
    return config.register_right_flag_buzzer(team, now_ms=_game(config).shown_at_ms + BUZZ_STREAM_LOCK_MS)


def _produced(before, after):
    return after.pending_events[len(before.pending_events):]


def test_starting_announces_a_country_and_shows_a_lookalike_first() -> None:
    game = _game(_running())

    assert game.phase == "running"
    assert game.round_number == 1
    assert COUNTRIES_BY_CODE[game.country_code].name == game.country_name
    assert len(game.flags) == FLAGS_PER_ROUND == len(set(game.flags))
    assert game.flag_index == 0 and game.flag_code == game.flags[0] != game.country_code
    assert game.deadline_ms == START_MS + flag_display_ms(1)
    assert game.scores == {team: 0 for team in TEAMS}


def test_an_unbuzzed_lookalike_scrolls_to_the_next_flag_of_the_same_country() -> None:
    running = _running()
    following = _game(running.expire_due_deadline(_game(running).deadline_ms))

    assert following.phase == "running"
    assert following.round_number == 1 and following.country_code == _game(running).country_code
    assert following.flag_index == 1 and following.flag_code == following.flags[1]


def test_buzzing_the_right_flag_scores_a_point_then_changes_country() -> None:
    found = _buzz(_scroll_until(_running(), target=True), "Bleus")
    game = _game(found)

    assert game.phase == "feedback" and game.answer_revealed
    assert game.scores == {"Rouges": 0, "Bleus": 1, "Verts": 0}
    assert game.verdict.correct and game.verdict.points == 1 and game.verdict.flag_code == game.country_code

    next_country = _game(found.expire_due_deadline(game.deadline_ms))
    assert next_country.round_number == 2 and next_country.phase == "running"
    assert next_country.country_code != game.country_code
    assert next_country.used_countries == [game.country_code, next_country.country_code]


def test_a_wrong_flag_costs_a_point_and_the_same_country_goes_on() -> None:
    scored = _buzz(_scroll_until(_running(), target=True), "Rouges")
    second_country = scored.expire_due_deadline(_game(scored).deadline_ms)

    wrong = _game(_buzz(second_country, "Rouges"))
    assert wrong.scores["Rouges"] == 0 and wrong.verdict.points == -1
    assert not wrong.verdict.correct and wrong.verdict.flag_code != wrong.country_code
    assert wrong.verdict.flag_country == COUNTRIES_BY_CODE[wrong.verdict.flag_code].name
    assert not wrong.answer_revealed

    floored = _game(_buzz(_running(), "Verts"))
    assert floored.scores["Verts"] == 0 and floored.verdict.points == 0

    resumed = _game(_buzz(_running(), "Verts").expire_due_deadline(floored.deadline_ms))
    assert resumed.round_number == 1 and resumed.flag_index == 1 and resumed.verdict is None


def test_a_missed_right_flag_is_revealed_without_point_then_the_country_changes() -> None:
    at_target = _scroll_until(_running(), target=True)
    missed = at_target.expire_due_deadline(_game(at_target).deadline_ms)
    game = _game(missed)

    assert game.phase == "feedback" and game.verdict is None and game.answer_revealed
    assert game.scores == {team: 0 for team in TEAMS}
    assert _produced(at_target, missed) == (FlagRevealed(game.country_code, found_by=None),)
    assert _game(missed.expire_due_deadline(game.deadline_ms)).round_number == 2


def test_buzzes_are_ignored_during_feedback_and_right_after_a_flag_appears() -> None:
    running = _running()
    assert running.register_right_flag_buzzer("Rouges", now_ms=START_MS + BUZZ_STREAM_LOCK_MS - 1) is running

    feedback = _buzz(running, "Rouges")
    assert feedback.register_right_flag_buzzer("Bleus", now_ms=_game(feedback).shown_at_ms + 900) is feedback


def test_pause_and_resume() -> None:
    paused = _running().pause_right_flag()
    assert _game(paused).phase == "paused"
    with pytest.raises(InvalidGameConfigError, match="pause"):
        paused.register_right_flag_buzzer("Rouges", now_ms=START_MS + 5_000)

    resumed = _game(paused.resume_right_flag(60_000))
    assert resumed.phase == "running" and resumed.flag_index == 1 and resumed.shown_at_ms == 60_000


def test_flags_scroll_faster_country_after_country() -> None:
    durations = [flag_display_ms(round_number) for round_number in range(1, 30)]

    assert durations == sorted(durations, reverse=True)
    assert durations[0] > durations[-1] >= 1_500


def test_the_first_team_to_five_wins_the_manche() -> None:
    current = _running()
    for _ in range(BUZZ_STREAM_WINNING_SCORE):
        current = _buzz(_scroll_until(current, target=True), "Verts")
        if _game(current).phase == "feedback":
            current = current.expire_due_deadline(_game(current).deadline_ms)

    game = _game(current)
    assert game.phase == "finished" and game.winner_team == "Verts"
    assert current.session.manche_winner == "Verts"


def test_only_the_controller_sees_the_right_flag_before_it_is_found() -> None:
    running = _running()
    controller, display = present_game_config(running)
    controller_game, display_game = controller["session"]["right_flag"], display["session"]["right_flag"]

    assert controller_game["country_code"] == _game(running).country_code
    assert display_game["country_code"] == "" and display_game["country_name"] == _game(running).country_name
    for view in (controller_game, display_game):
        assert "flags" not in view and "used_countries" not in view

    wrong = _buzz(running, "Rouges")
    assert present_game_config(wrong)[1]["session"]["right_flag"]["country_code"] == ""

    found = _buzz(_scroll_until(running, target=True), "Rouges")
    assert present_game_config(found)[1]["session"]["right_flag"]["country_code"] == _game(running).country_code


def test_domain_events_never_leak_the_right_flag_early() -> None:
    ready = started_config("right_flag", teams=TEAMS).pull_events()[0]
    running = ready.start_right_flag(START_MS)
    wrong = _buzz(running, "Rouges")
    found = _buzz(_scroll_until(wrong.expire_due_deadline(_game(wrong).deadline_ms), target=True), "Bleus")
    code = _game(running).country_code

    assert _produced(ready, running) == (CountryAnnounced(1, _game(running).country_name),)
    assert _produced(running, wrong) == (
        BuzzerPressed("right_flag", "Rouges"),
        AnswerJudged("right_flag", "Rouges", correct=False),
    )
    assert code not in repr(_produced(ready, wrong))
    assert FlagRevealed(code, found_by="Bleus") in found.pending_events


def test_persistence_round_trip() -> None:
    wrong = _buzz(_running(), "Rouges")

    assert game_config_from_payload(game_config_to_payload(wrong)).session.right_flag == _game(wrong)


def test_tampered_states_are_rejected() -> None:
    running = _running()
    game = _game(running)
    decoy = next(code for code in COUNTRIES_BY_CODE if code not in game.flags)

    for tampered, message in (
        (replace(game, country_name="Atlantide"), "pays"),
        (replace(game, flag_code=decoy), "série"),
        (replace(game, flags=game.flags[:-1]), "série"),
        (replace(game, flag_index=game.target_index + 1), "série"),
        (replace(game, used_countries=[]), "plusieurs fois"),
        (replace(game, scores={**game.scores, "Rouges": 9}), "scores"),
    ):
        with pytest.raises(InvalidGameConfigError, match=message):
            running._replace_session(right_flag=tampered).validate()


def test_display_buzzes_through_websocket_but_cannot_pause() -> None:
    at_target = _scroll_until(_running(), target=True)
    harness = GameHarness(at_target, now_ms=_game(at_target).shown_at_ms + BUZZ_STREAM_LOCK_MS)

    snapshot = harness.run("right-flag.buzzer", {"team": "Bleus"}, role=ClientRole.DISPLAY)
    assert _game(harness.config).scores["Bleus"] == 1
    assert [event["type"] for event in snapshot.events] == ["buzzer.pressed", "answer.judged", "right_flag.flag_revealed"]
    with pytest.raises(CommandNotAllowedError, match="lecture seule"):
        harness.run("right-flag.pause", role=ClientRole.DISPLAY)


def test_the_deadline_worker_scrolls_the_flags_and_a_hardware_buzzer_answers() -> None:
    clock = {"now": START_MS}
    harness = GameHarness(_running(), now_ms=lambda: clock["now"])

    clock["now"] = START_MS + flag_display_ms(1)
    snapshot = asyncio.run(harness.use_cases.game_night.expire_due_deadlines())
    assert snapshot is not None and snapshot.display["session"]["right_flag"]["flag_number"] == 2

    clock["now"] += BUZZ_STREAM_LOCK_MS
    asyncio.run(harness.use_cases.game_night.register_hardware_buzzer(TeamCommand(team="Verts")))
    assert _game(harness.config).verdict.team == "Verts"


def test_catalog_is_large_unique_and_well_formed() -> None:
    assert len(COUNTRIES) >= 120
    assert len(COUNTRIES_BY_CODE) == len(COUNTRIES)
    assert len({country.name for country in COUNTRIES}) == len(COUNTRIES)
    assert all(re.fullmatch(r"[A-Z]{2}", country.code) for country in COUNTRIES)
    families = {country.family for country in COUNTRIES}
    assert all(sum(country.family == family for country in COUNTRIES) > LOOKALIKES_PER_ROUND for family in families)


def test_a_round_mixes_lookalikes_never_starts_with_the_answer_and_avoids_repeats() -> None:
    rng = random.Random(3)
    used: list[str] = []
    for _ in range(len(COUNTRIES)):
        country, flags, restarted = pick_round(used, rng)
        assert not restarted and country.code not in used
        assert len(flags) == FLAGS_PER_ROUND == len(set(flags)) and flags.count(country.code) == 1
        assert flags[0] != country.code
        assert sum(COUNTRIES_BY_CODE[code].family == country.family for code in flags) >= LOOKALIKES_PER_ROUND + 1
        used.append(country.code)

    assert pick_round(used, rng)[2] is True
