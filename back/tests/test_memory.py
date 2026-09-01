from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import MEMORY_CHAIN_LENGTH, CultureQuestion, build_default_game_config
from infrastructure.game_config_payload_mapper import game_config_from_payload
from presentation.realtime.game_config_ws_handler import build_client_envelope, dispatch_game_config_event


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
        patch("domain.game_config.model.game_config.random.randrange", return_value=start_index),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", side_effect=questions),
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
        patch("domain.game_config.model.game_config.random.randrange", return_value=team_count - 1),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", return_value=first_question),
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

    with patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", return_value=next_question):
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
    with patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", return_value=next_question):
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
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", return_value=_question(1)),
    ):
        started = config.start_memory()

    with pytest.raises(InvalidGameConfigError, match="8 questions"):
        started.validate_memory_sequence()
    with pytest.raises(InvalidGameConfigError, match="déjà démarré"):
        started.start_memory()


def test_memory_payload_round_trip_and_legacy_active_state_migration() -> None:
    _, recitation, _ = _play_chain(_memory_config(), start_index=0)
    restored = game_config_from_payload(recitation.to_dict())

    assert restored.session.memory == recitation.session.memory
    assert restored.to_dict()["session"]["memory"]["sequence_length"] == MEMORY_CHAIN_LENGTH
    assert restored.to_dict()["session"]["memory"]["chain_length"] == MEMORY_CHAIN_LENGTH

    legacy_payload = recitation.to_dict()
    legacy_payload["session"]["memory"].pop("rules_version")
    legacy_payload["session"]["memory"]["phase"] = "question"
    migrated = game_config_from_payload(legacy_payload)
    assert migrated.session.memory.phase == "idle"
    assert migrated.session.memory.validated_answers == []


def test_legacy_finished_state_keeps_its_winner() -> None:
    _, recitation, _ = _play_chain(_memory_config(team_count=2), start_index=0)
    finished = recitation.disqualify_memory_team()
    payload = finished.to_dict()
    payload["session"]["memory"].pop("rules_version")

    restored = game_config_from_payload(payload)

    assert restored.session.memory.phase == "finished"
    assert restored.session.memory.winner_team == "Équipe 2"
    assert restored.session.memory.qualified_team_indices == [1]


def test_display_snapshot_never_contains_current_chain_answers() -> None:
    config = _memory_config()
    questions = [_question(1, "SECRET_"), _question(2, "SECRET_")]
    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", side_effect=questions),
    ):
        progressed = config.start_memory().next_memory_question()
    read_model = GameConfigReadModel.from_domain(progressed)

    controller = build_client_envelope("game.config.snapshot", read_model, "controller")
    display = build_client_envelope("game.config.snapshot", read_model, "display")
    controller_memory = controller["payload"]["session"]["memory"]
    display_memory = display["payload"]["session"]["memory"]

    assert controller_memory["validated_answers"] == [question.answer for question in questions]
    assert display_memory["validated_answers"] == []
    assert display_memory["sequence_length"] == 2
    assert display_memory["current_question"]["question"] == questions[-1].question
    assert display_memory["current_question"]["answer"] == "Réponse masquée"
    assert all(question.answer not in str(display) for question in questions)


class _MemoryCommandUseCase:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def start_memory(self):
        self.calls.append("start")
        return "started"

    async def next_memory_question(self):
        self.calls.append("next")
        return "next-question"

    async def validate_memory_sequence(self):
        self.calls.append("validate")
        return "validated"

    async def disqualify_memory_team(self):
        self.calls.append("disqualify")
        return "disqualified"


def test_memory_websocket_commands_are_controller_only_and_dispatched() -> None:
    command = _MemoryCommandUseCase()

    results = [asyncio.run(dispatch_game_config_event(
        client_type="controller",
        event_type=event_type,
        payload={},
        command_usecase=command,  # type: ignore[arg-type]
    )) for event_type in ("memory.start", "memory.next-question", "memory.validate-sequence", "memory.disqualify-team")]
    forbidden = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="memory.validate-sequence",
        payload={},
        command_usecase=command,  # type: ignore[arg-type]
    ))

    assert results == ["started", "next-question", "validated", "disqualified"]
    assert forbidden == {"type": "error", "detail": "Le client display est en lecture seule."}
    assert command.calls == ["start", "next", "validate", "disqualify"]
