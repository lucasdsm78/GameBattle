from __future__ import annotations

from collections import Counter

from domain.game_config.model.game_config import build_default_game_config, build_round_sequence


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


def test_read_model_does_not_expose_round_sequence() -> None:
    config = build_default_game_config().start_session()
    payload = config.to_dict()

    assert payload["session"]["round_sequence"]

    from application.game_config.game_config_models import GameConfigReadModel

    read_model_payload = GameConfigReadModel.from_domain(config).model_dump()
    assert "round_sequence" not in read_model_payload["session"]

