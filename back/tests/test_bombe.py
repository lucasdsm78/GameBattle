from __future__ import annotations

from unittest.mock import patch

import pytest

from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import (
    BOMBE_LETTERS,
    BOMBE_MAX_DURATION_MS,
    BOMBE_MIN_DURATION_MS,
    build_default_game_config,
)
from infrastructure.game_config_payload_mapper import game_config_from_payload


def _bombe_config(*, teams: list[str] | None = None):
    config = build_default_game_config()
    config.settings.teams = teams or ["Rouges", "Bleus"]
    config.settings.buzzer_keys = [str(index + 1) for index in range(len(config.settings.teams))]
    config.settings.total_rounds = 1
    for game in config.games:
        game.enabled = game.game_key == "bombe"
    return config.start_session()


def test_bombe_start_uses_secret_bounded_timer_and_random_team() -> None:
    config = _bombe_config(teams=["Rouges", "Bleus", "Verts"])

    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=2),
        patch("domain.game_config.model.game_config.random.randint", return_value=BOMBE_MIN_DURATION_MS),
        patch("domain.game_config.model.game_config.random.choice", return_value="M"),
    ):
        started = config.start_bombe(now_ms=1_000_000)

    bombe = started.session.bombe
    assert bombe.phase == "running"
    assert bombe.letter in BOMBE_LETTERS
    assert bombe.letter == "M"
    assert bombe.current_team_index == 2
    assert bombe.turn_history == [2]
    assert bombe.started_at_ms == 1_000_000
    assert BOMBE_MIN_DURATION_MS <= bombe.deadline_at_ms - bombe.started_at_ms <= BOMBE_MAX_DURATION_MS
    assert bombe.scores == {"Rouges": 0, "Bleus": 0, "Verts": 0}
    assert bombe.eligible_team_indices == [0, 1, 2]


def test_bombe_only_current_team_can_pass_then_presenter_can_go_back() -> None:
    config = _bombe_config(teams=["Rouges", "Bleus", "Verts"])
    with patch("domain.game_config.model.game_config.random.randrange", return_value=0):
        started = config.start_bombe(now_ms=10_000)

    with pytest.raises(InvalidGameConfigError, match="Rouges"):
        started.register_bombe_buzzer("Bleus", now_ms=10_001)

    passed = started.register_bombe_buzzer("Rouges", now_ms=10_001)
    assert passed.session.bombe.current_team_index == 1
    assert passed.session.bombe.turn_history == [0, 1]

    passed_again = passed.register_bombe_buzzer("Bleus", now_ms=10_002)
    assert passed_again.session.bombe.current_team_index == 2
    assert passed_again.session.bombe.turn_history == [0, 1, 2]

    rolled_back = passed_again.previous_bombe_team(now_ms=10_003)
    assert rolled_back.session.bombe.current_team_index == 1
    assert rolled_back.session.bombe.turn_history == [0, 1]


def test_bombe_cannot_go_back_without_previous_team() -> None:
    started = _bombe_config().start_bombe(now_ms=10_000)

    with pytest.raises(InvalidGameConfigError, match="précédente"):
        started.previous_bombe_team(now_ms=10_001)


def test_bombe_rejects_early_explosion_and_explodes_at_exact_deadline() -> None:
    config = _bombe_config(teams=["Rouges", "Bleus"])
    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch("domain.game_config.model.game_config.random.randint", return_value=BOMBE_MIN_DURATION_MS),
    ):
        started = config.start_bombe(now_ms=20_000)
    passed = started.register_bombe_buzzer("Rouges", now_ms=20_001)

    with pytest.raises(InvalidGameConfigError, match="pas encore explosé"):
        passed.explode_bombe(now_ms=passed.session.bombe.deadline_at_ms - 1)

    exploded = passed.explode_bombe(now_ms=passed.session.bombe.deadline_at_ms)
    assert exploded.session.bombe.phase == "exploded"
    assert exploded.session.bombe.exploded_team == "Bleus"
    assert exploded.session.bombe.winner_team == "Rouges"
    assert exploded.session.bombe.scores == {"Rouges": 0, "Bleus": 1}
    assert exploded.session.manche_finished is True
    assert exploded.session.manche_winner == "Rouges"
    assert exploded.session.active_round is not None
    assert exploded.session.active_round.completed is True
    assert exploded.explode_bombe(now_ms=exploded.session.bombe.deadline_at_ms + 1) is exploded


def test_bombe_tiebreak_keeps_lowest_scores_until_one_winner_remains() -> None:
    config = _bombe_config(teams=["Rouges", "Bleus", "Verts"])
    with patch("domain.game_config.model.game_config.random.randrange", return_value=0):
        started = config.start_bombe(now_ms=20_000)
    passed = started.register_bombe_buzzer("Rouges", now_ms=20_001)

    tied = passed.explode_bombe(now_ms=passed.session.bombe.deadline_at_ms)

    assert tied.session.bombe.scores == {"Rouges": 0, "Bleus": 1, "Verts": 0}
    assert tied.session.bombe.eligible_team_indices == [0, 2]
    assert tied.session.bombe.winner_team is None
    assert tied.session.manche_finished is False
    assert tied.session.active_round is not None
    assert tied.session.active_round.completed is False

    with patch("domain.game_config.model.game_config.random.randrange", return_value=0):
        restarted = tied.start_bombe(now_ms=tied.session.bombe.deadline_at_ms + 1)

    assert restarted.session.bombe.tiebreak_round == 1
    assert restarted.session.bombe.current_team_index == 0
    assert restarted.session.bombe.scores == tied.session.bombe.scores
    assert restarted.session.bombe.eligible_team_indices == [0, 2]

    decided = restarted.explode_bombe(now_ms=restarted.session.bombe.deadline_at_ms)

    assert decided.session.bombe.scores == {"Rouges": 1, "Bleus": 1, "Verts": 0}
    assert decided.session.bombe.eligible_team_indices == [2]
    assert decided.session.bombe.winner_team == "Verts"
    assert decided.session.manche_finished is True
    assert decided.session.manche_winner == "Verts"


def test_late_buzz_explodes_instead_of_passing_the_bombe() -> None:
    started = _bombe_config().start_bombe(now_ms=30_000)
    current_team = started.settings.teams[started.session.bombe.current_team_index]

    exploded = started.register_bombe_buzzer(current_team, now_ms=started.session.bombe.deadline_at_ms)

    assert exploded.session.bombe.phase == "exploded"
    assert exploded.session.bombe.exploded_team == current_team
    assert exploded.session.manche_finished is True


def test_bombe_payload_round_trip_preserves_running_state() -> None:
    started = _bombe_config(teams=["Rouges", "Bleus", "Verts"]).start_bombe(now_ms=40_000)
    current_team = started.settings.teams[started.session.bombe.current_team_index]
    passed = started.register_bombe_buzzer(current_team, now_ms=40_001)

    restored = game_config_from_payload(passed.to_dict())

    assert restored.session.bombe == passed.session.bombe
    assert restored.session.round_sequence == passed.session.round_sequence
    assert restored.to_dict()["session"]["bombe"] == passed.to_dict()["session"]["bombe"]


def test_legacy_running_bombe_payload_initializes_scores_and_eligible_teams() -> None:
    started = _bombe_config(teams=["Rouges", "Bleus", "Verts"]).start_bombe(now_ms=45_000)
    payload = started.to_dict()
    payload["session"]["bombe"].pop("scores")
    payload["session"]["bombe"].pop("eligible_team_indices")
    payload["session"]["bombe"].pop("tiebreak_round")

    restored = game_config_from_payload(payload)

    assert restored.session.bombe.scores == {"Rouges": 0, "Bleus": 0, "Verts": 0}
    assert restored.session.bombe.eligible_team_indices == [0, 1, 2]
    assert restored.session.bombe.tiebreak_round == 0


def test_bombe_winner_is_counted_in_final_ranking() -> None:
    started = _bombe_config().start_bombe(now_ms=50_000)
    current_team = started.settings.teams[started.session.bombe.current_team_index]
    exploded = started.explode_bombe(started.session.bombe.deadline_at_ms)
    winner = exploded.session.bombe.winner_team

    finished = exploded.next_manche()

    assert winner is not None
    assert winner != current_team
    assert finished.status == "finished"
    assert finished.session.manches_won[winner] == 1
    winner_entry = next(entry for entry in finished.session.final_ranking if entry["team"] == winner)
    assert winner_entry["rank"] == 1
