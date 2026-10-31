from __future__ import annotations

from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from domain.shared.services.scoring import TIE_LABEL
from domain.stopchrono.events import ChronoRoundStarted
from domain.stopchrono.models.stopchrono_state import (
    STOPCHRONO_ROUNDS,
    STOPCHRONO_TARGET_RANGES_S,
)
from exceptions import InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from support import started_config

TEAMS = ["Rouges", "Bleus", "Verts"]


def _chrono(teams: list[str] | None = None):
    return started_config("stopchrono", teams=teams or TEAMS).pull_events()[0]


def _game(config):
    return config.session.stopchrono


def _play_round(config, errors_ms: dict[str, int]):
    """Chaque équipe s'arrête à `errors_ms[équipe]` de la cible (en dépassant), dans l'ordre du tour."""
    teams = config.settings.teams
    for _ in teams:
        game = _game(config)
        team = teams[game.current_team_index]
        start = 1_000_000 * (len(game.results) + 1) + 10_000_000 * game.round_number
        config = config.start_chrono(start).stop_chrono(start + game.target_ms + errors_ms[team]).next_chrono_team()
    return config


def test_a_manche_has_three_rounds_with_growing_targets() -> None:
    config = _chrono()
    targets = []
    for _ in range(STOPCHRONO_ROUNDS):
        targets.append(_game(config).target_ms)
        config = _play_round(config, {team: 0 for team in TEAMS})

    for target, (low, high) in zip(targets, STOPCHRONO_TARGET_RANGES_S):
        assert low * 1000 <= target <= high * 1000
    assert targets == sorted(targets)
    assert _game(config).phase == "finished"


def test_each_round_starts_with_the_next_team() -> None:
    config = _chrono()
    assert _game(config).current_team_index == 0

    second = _play_round(config, {team: 0 for team in TEAMS})
    assert _game(second).round_number == 2 and _game(second).current_team_index == 1
    assert _game(second).results == {} and _game(second).phase == "idle"

    third = _play_round(second, {team: 0 for team in TEAMS})
    assert _game(third).round_number == 3 and _game(third).current_team_index == 2


def test_within_a_round_every_team_plays_once_in_rotation() -> None:
    second = _play_round(_chrono(), {team: 0 for team in TEAMS})
    order = []
    for _ in TEAMS:
        game = _game(second)
        order.append(TEAMS[game.current_team_index])
        second = second.start_chrono(1).stop_chrono(1 + game.target_ms).next_chrono_team()

    assert order == ["Bleus", "Verts", "Rouges"]


def test_errors_add_up_and_the_smallest_total_wins() -> None:
    config = _chrono()
    config = _play_round(config, {"Rouges": 100, "Bleus": 900, "Verts": 300})
    config = _play_round(config, {"Rouges": 700, "Bleus": 50, "Verts": 300})
    config = _play_round(config, {"Rouges": 100, "Bleus": 100, "Verts": 300})
    game = _game(config)

    assert game.total_errors_ms(TEAMS) == {"Rouges": 900, "Bleus": 1_050, "Verts": 900}
    assert game.phase == "finished" and game.winner_team == TIE_LABEL
    assert game.scores == {"Rouges": 1, "Bleus": 0, "Verts": 1}


def test_a_single_best_total_wins_the_manche() -> None:
    config = _chrono(["Rouges", "Bleus"])
    for errors in ({"Rouges": 400, "Bleus": 100}, {"Rouges": 100, "Bleus": 100}, {"Rouges": 100, "Bleus": 100}):
        config = _play_round(config, errors)

    assert _game(config).winner_team == "Bleus" and config.session.manche_winner == "Bleus"


def test_a_new_round_is_announced() -> None:
    config = _chrono()
    before = config
    for _ in TEAMS[:-1]:
        game = _game(before)
        before = before.start_chrono(1).stop_chrono(1 + game.target_ms).next_chrono_team()
    last = _game(before)
    stopped = before.start_chrono(1).stop_chrono(1 + last.target_ms)
    new_round = stopped.next_chrono_team()

    produced = new_round.pending_events[len(stopped.pending_events):]
    assert produced == (ChronoRoundStarted(2, _game(new_round).target_ms // 1000, first_team="Bleus"),)


def test_clients_see_the_round_and_the_running_totals() -> None:
    config = _play_round(_chrono(), {"Rouges": 100, "Bleus": 200, "Verts": 300})
    payload = present_game_config(config)[1]["session"]["stopchrono"]

    assert payload["round_number"] == 2 and payload["rounds_total"] == STOPCHRONO_ROUNDS
    assert payload["total_errors_ms"] == {"Rouges": 100, "Bleus": 200, "Verts": 300}
    assert payload["past_targets_ms"] == [_game(config).past_targets_ms[0]]


def test_persistence_round_trip_and_a_state_saved_before_the_rounds_still_loads() -> None:
    config = _play_round(_chrono(), {team: 0 for team in TEAMS})
    assert game_config_from_payload(game_config_to_payload(config)).session.stopchrono == _game(config)

    legacy = game_config_to_payload(_chrono())
    for key in ("round_number", "past_targets_ms", "past_results"):
        del legacy["session"]["stopchrono"][key]
    legacy["session"]["stopchrono"]["target_ms"] = 21_000  # ancienne cible, tirée entre 7 et 25 s
    assert game_config_from_payload(legacy).session.stopchrono.round_number == 1


def test_tampered_rounds_are_rejected() -> None:
    config = _play_round(_chrono(), {team: 0 for team in TEAMS})
    game = _game(config)

    for tampered in (
        replace(game, round_number=STOPCHRONO_ROUNDS + 1),
        replace(game, past_targets_ms=[]),
        replace(game, past_results=[{"Rouges": 1}]),
    ):
        with pytest.raises(InvalidGameConfigError, match="tours du stop chrono"):
            config._replace_session(stopchrono=tampered).validate()
