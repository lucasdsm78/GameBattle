from __future__ import annotations

from unittest.mock import patch

import pytest

from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import (
    BOMBE_DIE_ROLL_MS,
    BOMBE_MAX_DURATION_MS,
    BOMBE_MIN_DURATION_MS,
    build_default_game_config,
)
from infrastructure.game_config_payload_mapper import game_config_from_payload


def _bombe_config(*, teams: list[str] | None = None, total_rounds: int = 1):
    config = build_default_game_config()
    config.settings.teams = teams or ["Rouges", "Bleus"]
    config.settings.buzzer_keys = [str(index + 1) for index in range(len(config.settings.teams))]
    config.settings.total_rounds = total_rounds
    for game in config.games:
        game.enabled = game.game_key == "bombe"
    return config.start_session()


def _running_bombe(config, *, now_ms: int):
    prepared = config.start_bombe(now_ms=now_ms)
    roller = config.settings.teams[prepared.session.bombe.roller_team_index or 0]
    rolling = prepared.register_bombe_buzzer(roller, now_ms=now_ms + 1)
    return rolling.begin_bombe_after_roll(now_ms=now_ms + BOMBE_DIE_ROLL_MS + 1)


def test_bombe_prepares_random_sound_and_starts_timer_only_after_die_roll() -> None:
    config = _bombe_config(teams=["Rouges", "Bleus", "Verts"])

    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=2),
        patch("domain.game_config.model.game_config.random.randint", return_value=BOMBE_MIN_DURATION_MS),
        patch("domain.game_config.model.game_config.random.choice", side_effect=["OL", "TIC"]),
    ):
        prepared = config.start_bombe(now_ms=1_000_000)
        assert prepared.session.bombe.phase == "awaiting_roll"
        assert prepared.session.bombe.sound == "OL"
        assert prepared.session.bombe.roller_team_index == 2
        assert prepared.session.bombe.deadline_at_ms == 0

        with pytest.raises(InvalidGameConfigError, match="Verts"):
            prepared.register_bombe_buzzer("Rouges", now_ms=1_000_001)

        rolling = prepared.register_bombe_buzzer("Verts", now_ms=1_000_001)
        assert rolling.session.bombe.phase == "rolling"
        assert rolling.session.bombe.die_result == "TIC"
        assert rolling.session.bombe.die_reveal_at_ms == 1_000_001 + BOMBE_DIE_ROLL_MS

        with pytest.raises(InvalidGameConfigError, match="tourne encore"):
            rolling.begin_bombe_after_roll(now_ms=rolling.session.bombe.die_reveal_at_ms - 1)
        started = rolling.begin_bombe_after_roll(now_ms=rolling.session.bombe.die_reveal_at_ms)

    bombe = started.session.bombe
    assert bombe.phase == "running"
    assert bombe.current_team_index == 2
    assert bombe.turn_history == [2]
    assert bombe.started_at_ms == rolling.session.bombe.die_reveal_at_ms
    assert BOMBE_MIN_DURATION_MS <= bombe.deadline_at_ms - bombe.started_at_ms <= BOMBE_MAX_DURATION_MS
    assert bombe.scores == {"Rouges": 0, "Bleus": 0, "Verts": 0}
    assert bombe.eligible_team_indices == [0, 1, 2]


def test_bombe_only_current_team_can_pass_then_presenter_can_go_back() -> None:
    config = _bombe_config(teams=["Rouges", "Bleus", "Verts"])
    with patch("domain.game_config.model.game_config.random.randrange", return_value=0):
        started = _running_bombe(config, now_ms=10_000)

    with pytest.raises(InvalidGameConfigError, match="Rouges"):
        started.register_bombe_buzzer("Bleus", now_ms=started.session.bombe.started_at_ms + 1)

    passed = started.register_bombe_buzzer("Rouges", now_ms=started.session.bombe.started_at_ms + 1)
    assert passed.session.bombe.current_team_index == 1
    assert passed.session.bombe.turn_history == [0, 1]

    passed_again = passed.register_bombe_buzzer("Bleus", now_ms=started.session.bombe.started_at_ms + 2)
    assert passed_again.session.bombe.current_team_index == 2
    assert passed_again.session.bombe.turn_history == [0, 1, 2]

    rolled_back = passed_again.previous_bombe_team(now_ms=started.session.bombe.started_at_ms + 3)
    assert rolled_back.session.bombe.current_team_index == 1
    assert rolled_back.session.bombe.turn_history == [0, 1]


def test_bombe_cannot_go_back_without_previous_team() -> None:
    started = _running_bombe(_bombe_config(), now_ms=10_000)

    with pytest.raises(InvalidGameConfigError, match="précédente"):
        started.previous_bombe_team(now_ms=started.session.bombe.started_at_ms + 1)


def test_bombe_rejects_early_explosion_and_explodes_at_exact_deadline() -> None:
    config = _bombe_config(teams=["Rouges", "Bleus"])
    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch("domain.game_config.model.game_config.random.randint", return_value=BOMBE_MIN_DURATION_MS),
    ):
        started = _running_bombe(config, now_ms=20_000)
    passed = started.register_bombe_buzzer("Rouges", now_ms=started.session.bombe.started_at_ms + 1)

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
        started = _running_bombe(config, now_ms=20_000)
    passed = started.register_bombe_buzzer("Rouges", now_ms=started.session.bombe.started_at_ms + 1)

    tied = passed.explode_bombe(now_ms=passed.session.bombe.deadline_at_ms)

    assert tied.session.bombe.scores == {"Rouges": 0, "Bleus": 1, "Verts": 0}
    assert tied.session.bombe.eligible_team_indices == [0, 2]
    assert tied.session.bombe.winner_team is None
    assert tied.session.manche_finished is False
    assert tied.session.active_round is not None
    assert tied.session.active_round.completed is False

    with patch("domain.game_config.model.game_config.random.randrange", return_value=0):
        prepared = tied.start_bombe(now_ms=tied.session.bombe.deadline_at_ms + 1)
        roller = prepared.settings.teams[prepared.session.bombe.roller_team_index or 0]
        rolling = prepared.register_bombe_buzzer(roller, now_ms=tied.session.bombe.deadline_at_ms + 2)
        restarted = rolling.begin_bombe_after_roll(now_ms=rolling.session.bombe.die_reveal_at_ms)

    assert restarted.session.bombe.tiebreak_round == 1
    assert restarted.session.bombe.current_team_index == 2
    assert restarted.session.bombe.scores == tied.session.bombe.scores
    assert restarted.session.bombe.eligible_team_indices == [0, 2]

    decided = restarted.explode_bombe(now_ms=restarted.session.bombe.deadline_at_ms)

    assert decided.session.bombe.scores == {"Rouges": 0, "Bleus": 1, "Verts": 1}
    assert decided.session.bombe.eligible_team_indices == [0]
    assert decided.session.bombe.winner_team == "Rouges"
    assert decided.session.manche_finished is True
    assert decided.session.manche_winner == "Rouges"


def test_late_buzz_explodes_instead_of_passing_the_bombe() -> None:
    started = _running_bombe(_bombe_config(), now_ms=30_000)
    current_team = started.settings.teams[started.session.bombe.current_team_index]

    exploded = started.register_bombe_buzzer(current_team, now_ms=started.session.bombe.deadline_at_ms)

    assert exploded.session.bombe.phase == "exploded"
    assert exploded.session.bombe.exploded_team == current_team
    assert exploded.session.manche_finished is True


def test_bombe_payload_round_trip_preserves_running_state() -> None:
    started = _running_bombe(_bombe_config(teams=["Rouges", "Bleus", "Verts"]), now_ms=40_000)
    current_team = started.settings.teams[started.session.bombe.current_team_index]
    passed = started.register_bombe_buzzer(current_team, now_ms=40_001)

    restored = game_config_from_payload(passed.to_dict())

    assert restored.session.bombe == passed.session.bombe
    assert restored.session.round_sequence == passed.session.round_sequence
    assert restored.to_dict()["session"]["bombe"] == passed.to_dict()["session"]["bombe"]


def test_legacy_running_bombe_payload_initializes_scores_and_eligible_teams() -> None:
    started = _running_bombe(_bombe_config(teams=["Rouges", "Bleus", "Verts"]), now_ms=45_000)
    payload = started.to_dict()
    payload["session"]["bombe"].pop("scores")
    payload["session"]["bombe"].pop("eligible_team_indices")
    payload["session"]["bombe"].pop("tiebreak_round")

    restored = game_config_from_payload(payload)

    assert restored.session.bombe.scores == {"Rouges": 0, "Bleus": 0, "Verts": 0}
    assert restored.session.bombe.eligible_team_indices == [0, 1, 2]
    assert restored.session.bombe.tiebreak_round == 0


def test_bombe_winner_is_counted_in_final_ranking() -> None:
    started = _running_bombe(_bombe_config(), now_ms=50_000)
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


def test_next_bombe_round_uses_the_team_after_previous_roller() -> None:
    config = _bombe_config(total_rounds=2)
    with patch("domain.game_config.model.game_config.random.randrange", return_value=0):
        first = _running_bombe(config, now_ms=60_000)

    assert first.session.bombe.roller_team_index == 0
    finished_first = first.explode_bombe(first.session.bombe.deadline_at_ms)
    second_round = finished_first.next_manche()
    prepared_second = second_round.start_bombe(finished_first.session.bombe.deadline_at_ms + 1)

    assert prepared_second.session.bombe.phase == "awaiting_roll"
    assert prepared_second.session.bombe.roller_team_index == 1
    assert prepared_second.session.last_bombe_roller_index == 1
