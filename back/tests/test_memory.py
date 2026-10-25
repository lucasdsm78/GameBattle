from __future__ import annotations

from unittest.mock import patch

import pytest

from application.game_night.game_config_presenter import present_game_config
from application.shared.snapshot import ClientRole
from domain.game_night.models.game_config import build_default_game_config
from domain.memory.models.memory_state import MEMORY_CHAIN_LENGTH
from domain.shared.models.culture_question import CultureQuestion
from exceptions import CommandNotAllowedError, InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from support import GameHarness


def _question(index: int, prefix: str = "") -> CultureQuestion:
    marker = f"{prefix}{index}"
    return CultureQuestion(
        id=f"question-{marker}",
        question=f"Question {marker} ?",
        answer=f"Réponse {marker}",
        explanation=f"Explication secrète {marker}",
        difficulty="facile",
    )


def _memory_config(*, team_count: int = 3):
    config = build_default_game_config()
    config.settings.teams = [f"Équipe {index + 1}" for index in range(team_count)]
    config.settings.buzzer_keys = [str(index + 1) for index in range(team_count)]
    config.settings.total_rounds = 1
    for game in config.games:
        game.enabled = game.game_key == "memory"
    return config.start_session()


def _play_chain(config, *, start_index: int = 0, prefix: str = ""):
    questions = [_question(index, prefix) for index in range(1, MEMORY_CHAIN_LENGTH + 1)]
    with (
        patch("domain.memory.models.memory_state.random.randrange", return_value=start_index),
        patch("domain.memory.models.memory_state.pick_memory_question", side_effect=questions),
    ):
        current = config.start_memory()
        for _ in range(MEMORY_CHAIN_LENGTH - 1):
            current = current.next_memory_question()
        recitation = current.next_memory_question()
    return current, recitation, questions


@pytest.mark.parametrize("team_count", range(2, 7))
def test_memory_starts_first_team_chain_with_every_team_qualified(team_count: int) -> None:
    config = _memory_config(team_count=team_count)
    first_question = _question(1)

    with (
        patch("domain.memory.models.memory_state.random.randrange", return_value=team_count - 1),
        patch("domain.memory.models.memory_state.pick_memory_question", return_value=first_question),
    ):
        started = config.start_memory()

    memory = started.session.memory
    assert memory.phase == "question"
    assert memory.current_team_index == team_count - 1
    assert memory.qualified_team_indices == list(range(team_count))
    assert memory.validated_answers == [first_question.answer]
    assert memory.asked_questions == [first_question.question]
    assert memory.turn_number == 1


def test_eight_questions_keep_same_team_then_open_recitation() -> None:
    eighth_question, recitation, questions = _play_chain(_memory_config(), start_index=1)

    assert eighth_question.session.memory.phase == "question"
    assert eighth_question.session.memory.current_team_index == 1
    assert eighth_question.session.memory.current_question == questions[-1]
    assert eighth_question.session.memory.turn_number == MEMORY_CHAIN_LENGTH
    assert eighth_question.session.memory.validated_answers == [question.answer for question in questions]

    memory = recitation.session.memory
    assert memory.phase == "recitation"
    assert memory.current_team_index == 1
    assert memory.current_question is None
    assert memory.turn_number == MEMORY_CHAIN_LENGTH
    assert memory.validated_answers == [question.answer for question in questions]


def test_correct_sequence_moves_to_next_team_with_a_fresh_chain() -> None:
    _, recitation, first_chain = _play_chain(_memory_config(), start_index=1, prefix="A")
    next_question = _question(1, "B")

    with patch("domain.memory.models.memory_state.pick_memory_question", return_value=next_question):
        next_team = recitation.validate_memory_sequence()

    memory = next_team.session.memory
    assert memory.phase == "question"
    assert memory.current_team_index == 2
    assert memory.turn_number == 1
    assert memory.validated_answers == [next_question.answer]
    assert memory.current_question == next_question
    assert memory.asked_questions == [*[question.question for question in first_chain], next_question.question]


def test_fault_is_allowed_only_after_eight_questions_and_resets_next_team_chain() -> None:
    config = _memory_config(team_count=3)
    with pytest.raises(InvalidGameConfigError, match="8 questions"):
        config.disqualify_memory_team()

    _, recitation, _ = _play_chain(config, start_index=0)
    next_question = _question(1, "B")
    with patch("domain.memory.models.memory_state.pick_memory_question", return_value=next_question):
        continued = recitation.disqualify_memory_team()

    memory = continued.session.memory
    assert memory.current_team_index == 1
    assert memory.qualified_team_indices == [1, 2]
    assert memory.disqualified_teams == ["Équipe 1"]
    assert memory.phase == "question"
    assert memory.turn_number == 1
    assert memory.validated_answers == [next_question.answer]


def test_last_qualified_team_wins_and_is_counted_in_final_ranking() -> None:
    _, recitation, _ = _play_chain(_memory_config(team_count=2), start_index=0)
    finished_round = recitation.disqualify_memory_team()

    memory = finished_round.session.memory
    assert memory.phase == "finished"
    assert memory.current_question is None
    assert memory.qualified_team_indices == [1]
    assert memory.disqualified_teams == ["Équipe 1"]
    assert memory.winner_team == "Équipe 2"
    assert finished_round.session.manche_finished is True
    assert finished_round.session.active_round is not None
    assert finished_round.session.active_round.completed is True

    finished_game = finished_round.next_manche()
    assert finished_game.status == "finished"
    assert finished_game.session.manches_won["Équipe 2"] == 1
    winner = next(row for row in finished_game.session.final_ranking if row["team"] == "Équipe 2")
    assert winner["rank"] == 1


def test_memory_rejects_sequence_validation_before_recitation() -> None:
    config = _memory_config()
    with pytest.raises(InvalidGameConfigError, match="8 questions"):
        config.validate_memory_sequence()

    with (
        patch("domain.memory.models.memory_state.random.randrange", return_value=0),
        patch("domain.memory.models.memory_state.pick_memory_question", return_value=_question(1)),
    ):
        started = config.start_memory()

    with pytest.raises(InvalidGameConfigError, match="8 questions"):
        started.validate_memory_sequence()
    with pytest.raises(InvalidGameConfigError, match="déjà démarré"):
        started.start_memory()


def test_memory_payload_round_trip_and_legacy_active_state_migration() -> None:
    _, recitation, _ = _play_chain(_memory_config(), start_index=0)
    restored = game_config_from_payload(game_config_to_payload(recitation))

    assert restored.session.memory == recitation.session.memory
    assert present_game_config(restored)[0]["session"]["memory"]["sequence_length"] == MEMORY_CHAIN_LENGTH
    assert present_game_config(restored)[0]["session"]["memory"]["chain_length"] == MEMORY_CHAIN_LENGTH

    legacy_payload = game_config_to_payload(recitation)
    legacy_payload["session"]["memory"].pop("rules_version")
    legacy_payload["session"]["memory"]["phase"] = "question"
    migrated = game_config_from_payload(legacy_payload)
    assert migrated.session.memory.phase == "idle"
    assert migrated.session.memory.validated_answers == []


def test_legacy_finished_state_keeps_its_winner() -> None:
    _, recitation, _ = _play_chain(_memory_config(team_count=2), start_index=0)
    finished = recitation.disqualify_memory_team()
    payload = game_config_to_payload(finished)
    payload["session"]["memory"].pop("rules_version")

    restored = game_config_from_payload(payload)

    assert restored.session.memory.phase == "finished"
    assert restored.session.memory.winner_team == "Équipe 2"
    assert restored.session.memory.qualified_team_indices == [1]


def test_display_snapshot_never_contains_current_chain_answers() -> None:
    config = _memory_config()
    questions = [_question(1, "SECRET_"), _question(2, "SECRET_")]
    with (
        patch("domain.memory.models.memory_state.random.randrange", return_value=0),
        patch("domain.memory.models.memory_state.pick_memory_question", side_effect=questions),
    ):
        progressed = config.start_memory().next_memory_question()
    controller, display = present_game_config(progressed)
    controller_memory = controller["session"]["memory"]
    display_memory = display["session"]["memory"]

    assert controller_memory["validated_answers"] == [question.answer for question in questions]
    assert display_memory["validated_answers"] == []
    assert display_memory["sequence_length"] == 2
    assert display_memory["current_question"]["question"] == questions[-1].question
    assert display_memory["current_question"]["answer"] == "Réponse masquée"
    assert all(question.answer not in str(display) for question in questions)


def test_memory_commands_are_controller_only() -> None:
    harness = GameHarness(_memory_config())

    with patch("domain.memory.models.memory_state.pick_memory_question", side_effect=lambda asked: _question(len(asked) + 1)):
        harness.run("memory.start")
        harness.run("memory.next-question")
    with pytest.raises(CommandNotAllowedError, match="lecture seule"):
        harness.run("memory.validate-sequence", role=ClientRole.DISPLAY)

    assert harness.config.session.memory.turn_number == 2
    assert harness.repository.saves == 2
