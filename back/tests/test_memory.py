from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from application.game_config.game_config_models import GameConfigReadModel
from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import CultureQuestion, build_default_game_config
from infrastructure.game_config_payload_mapper import game_config_from_payload
from presentation.realtime.game_config_ws_handler import build_client_envelope, dispatch_game_config_event


def _question(identifier: str, answer: str) -> CultureQuestion:
    return CultureQuestion(
        id=identifier,
        question=f"Question {identifier} ?",
        answer=answer,
        explanation=f"Explication secrète {identifier}",
        difficulty="facile",
    )


def _memory_config(*, team_count: int = 3, total_rounds: int = 1):
    config = build_default_game_config()
    config.settings.teams = [f"Équipe {index + 1}" for index in range(team_count)]
    config.settings.buzzer_keys = [str(index + 1) for index in range(team_count)]
    config.settings.total_rounds = total_rounds
    for game in config.games:
        game.enabled = game.game_key == "memory"
    return config.start_session()


@pytest.mark.parametrize("team_count", range(2, 7))
def test_memory_starts_with_every_team_qualified(team_count: int) -> None:
    config = _memory_config(team_count=team_count)

    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=team_count - 1),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", return_value=_question("one", "Alpha")),
    ):
        started = config.start_memory()

    assert started.session.memory.phase == "question"
    assert started.session.memory.current_team_index == team_count - 1
    assert started.session.memory.qualified_team_indices == list(range(team_count))
    assert started.session.memory.disqualified_teams == []
    assert started.session.memory.validated_answers == []
    assert started.session.memory.turn_number == 1


def test_valid_answer_appends_the_answer_in_order_and_rotates() -> None:
    config = _memory_config(team_count=3)
    questions = [_question("one", "Alpha"), _question("two", "Bravo"), _question("three", "Charlie")]

    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=1),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", side_effect=questions),
    ):
        first = config.start_memory()
        second = first.validate_memory_answer()
        third = second.validate_memory_answer()

    assert second.session.memory.current_team_index == 2
    assert third.session.memory.current_team_index == 0
    assert third.session.memory.validated_answers == ["Alpha", "Bravo"]
    assert third.session.memory.asked_questions == ["Question one ?", "Question two ?"]
    assert third.session.memory.current_question == questions[2]
    assert third.session.memory.turn_number == 3


def test_disqualification_abandons_current_answer_and_skips_eliminated_teams() -> None:
    config = _memory_config(team_count=4)
    questions = [_question("one", "Alpha"), _question("two", "Bravo"), _question("three", "Charlie")]

    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", side_effect=questions),
    ):
        started = config.start_memory()
        after_first_fault = started.disqualify_memory_team()
        after_validation = after_first_fault.validate_memory_answer()

    memory = after_validation.session.memory
    assert after_first_fault.session.memory.current_team_index == 1
    assert after_first_fault.session.memory.disqualified_teams == ["Équipe 1"]
    assert after_first_fault.session.memory.validated_answers == []
    assert after_validation.session.memory.current_team_index == 2
    assert memory.validated_answers == ["Bravo"]
    assert memory.asked_questions == ["Question one ?", "Question two ?"]


def test_last_qualified_team_wins_and_is_counted_in_final_ranking() -> None:
    config = _memory_config(team_count=3)

    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch(
            "domain.game_config.model.game_config.GameConfig._pick_memory_question",
            side_effect=[_question("one", "Alpha"), _question("two", "Bravo")],
        ),
    ):
        started = config.start_memory()
        two_left = started.disqualify_memory_team()
        finished_round = two_left.disqualify_memory_team()

    memory = finished_round.session.memory
    assert memory.phase == "finished"
    assert memory.current_question is None
    assert memory.qualified_team_indices == [2]
    assert memory.disqualified_teams == ["Équipe 1", "Équipe 2"]
    assert memory.winner_team == "Équipe 3"
    assert finished_round.session.manche_finished is True
    assert finished_round.session.manche_winner == "Équipe 3"
    assert finished_round.session.active_round is not None
    assert finished_round.session.active_round.completed is True

    finished_game = finished_round.next_manche()
    assert finished_game.status == "finished"
    assert finished_game.session.manches_won["Équipe 3"] == 1
    winner = next(row for row in finished_game.session.final_ranking if row["team"] == "Équipe 3")
    assert winner["rank"] == 1


def test_memory_rejects_invalid_transitions() -> None:
    config = _memory_config(team_count=2)

    with pytest.raises(InvalidGameConfigError, match="réponse"):
        config.validate_memory_answer()
    with pytest.raises(InvalidGameConfigError, match="disqualifiée"):
        config.disqualify_memory_team()

    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch("domain.game_config.model.game_config.GameConfig._pick_memory_question", return_value=_question("one", "Alpha")),
    ):
        started = config.start_memory()

    with pytest.raises(InvalidGameConfigError, match="déjà démarré"):
        started.start_memory()


def test_memory_payload_round_trip_and_legacy_default() -> None:
    config = _memory_config(team_count=3)
    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch(
            "domain.game_config.model.game_config.GameConfig._pick_memory_question",
            side_effect=[_question("one", "Alpha"), _question("two", "Bravo")],
        ),
    ):
        progressed = config.start_memory().validate_memory_answer()

    restored = game_config_from_payload(progressed.to_dict())
    assert restored.session.memory == progressed.session.memory
    assert restored.to_dict()["session"]["memory"]["sequence_length"] == 1

    legacy_payload = build_default_game_config().to_dict()
    legacy_payload["session"].pop("memory")
    legacy = game_config_from_payload(legacy_payload)
    assert legacy.session.memory.phase == "idle"
    assert legacy.session.memory.validated_answers == []


def test_display_snapshot_never_contains_memory_answers_but_controller_does() -> None:
    config = _memory_config(team_count=3)
    with (
        patch("domain.game_config.model.game_config.random.randrange", return_value=0),
        patch(
            "domain.game_config.model.game_config.GameConfig._pick_memory_question",
            side_effect=[_question("one", "SECRET_ALPHA"), _question("two", "SECRET_BRAVO")],
        ),
    ):
        progressed = config.start_memory().validate_memory_answer()
    read_model = GameConfigReadModel.from_domain(progressed)

    controller = build_client_envelope("game.config.snapshot", read_model, "controller")
    display = build_client_envelope("game.config.snapshot", read_model, "display")
    controller_memory = controller["payload"]["session"]["memory"]
    display_memory = display["payload"]["session"]["memory"]

    assert controller_memory["validated_answers"] == ["SECRET_ALPHA"]
    assert controller_memory["current_question"]["answer"] == "SECRET_BRAVO"
    assert display_memory["validated_answers"] == []
    assert display_memory["sequence_length"] == 1
    assert display_memory["current_question"]["question"] == "Question two ?"
    assert display_memory["current_question"]["answer"] == "Réponse masquée"
    assert display_memory["current_question"]["explanation"] == ""
    assert "SECRET_ALPHA" not in str(display)
    assert "SECRET_BRAVO" not in str(display)


class _MemoryCommandUseCase:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def start_memory(self):
        self.calls.append("start")
        return "started"

    async def validate_memory_answer(self):
        self.calls.append("validate")
        return "validated"

    async def disqualify_memory_team(self):
        self.calls.append("disqualify")
        return "disqualified"


def test_memory_websocket_commands_are_controller_only_and_dispatched() -> None:
    command = _MemoryCommandUseCase()

    start = asyncio.run(dispatch_game_config_event(
        client_type="controller",
        event_type="memory.start",
        payload={},
        command_usecase=command,  # type: ignore[arg-type]
    ))
    validate = asyncio.run(dispatch_game_config_event(
        client_type="controller",
        event_type="memory.validate-answer",
        payload={},
        command_usecase=command,  # type: ignore[arg-type]
    ))
    disqualify = asyncio.run(dispatch_game_config_event(
        client_type="controller",
        event_type="memory.disqualify-team",
        payload={},
        command_usecase=command,  # type: ignore[arg-type]
    ))
    forbidden = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="memory.validate-answer",
        payload={},
        command_usecase=command,  # type: ignore[arg-type]
    ))

    assert (start, validate, disqualify) == ("started", "validated", "disqualified")
    assert forbidden == {"type": "error", "detail": "Le client display est en lecture seule."}
    assert command.calls == ["start", "validate", "disqualify"]
