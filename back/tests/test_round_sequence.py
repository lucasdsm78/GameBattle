from __future__ import annotations

from collections import Counter

import pytest

from application.game_night.game_config_presenter import present_game_config
from domain.game_night.models.game_config import build_default_game_config
from domain.game_night.services.round_sequence import build_round_sequence
from exceptions import InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import game_config_to_payload


def test_random_round_sequence_is_balanced_and_has_expected_length() -> None:
    sequence = build_round_sequence(["blindtest", "stopchrono", "culture"], total=14, random_order=True)
    counts = Counter(sequence)

    assert len(sequence) == 14
    assert set(sequence) == {"blindtest", "stopchrono", "culture"}
    assert max(counts.values()) - min(counts.values()) <= 1


def test_random_round_sequence_avoids_adjacent_duplicates_when_possible() -> None:
    sequence = build_round_sequence(["blindtest", "stopchrono"], total=10, random_order=True)

    assert len(sequence) == 10
    assert all(current != previous for previous, current in zip(sequence, sequence[1:]))


def test_manual_round_sequence_uses_predictable_round_robin_order() -> None:
    sequence = build_round_sequence(["blindtest", "stopchrono"], total=5, random_order=False)

    assert sequence == ["blindtest", "stopchrono", "blindtest", "stopchrono", "blindtest"]


def test_client_views_never_expose_round_sequence() -> None:
    config = build_default_game_config().start_session()

    assert game_config_to_payload(config)["session"]["round_sequence"]
    assert all("round_sequence" not in view["session"] for view in present_game_config(config))


def test_culture_next_question_requires_correct_answer() -> None:
    config = build_default_game_config()
    config.games[0].enabled = False
    config.games[2].enabled = True
    config = config.start_session().start_culture().select_culture_difficulty("facile")

    with pytest.raises(InvalidGameConfigError):
        config.next_culture_question()

    answered = config.register_culture_buzzer(config.settings.teams[0]).answer_culture(True)
    next_question = answered.next_culture_question()

    assert next_question.session.culture.phase == "selecting"
    assert next_question.session.culture.current_index == 2


