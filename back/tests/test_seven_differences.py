from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from application.game_config.game_config_models import BlindtestBuzzerCommandModel, GameConfigReadModel
from application.seven_differences.seven_differences_command_usecase import SevenDifferencesCommandUseCase
from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import SEVEN_DIFFERENCES_MEMORIZATION_MS, TIE_LABEL, build_default_game_config
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.game_config_payload_mapper import game_config_from_payload
from presentation.realtime.game_config_ws_handler import build_client_envelope, dispatch_game_config_event


def _seven_config(*, teams: list[str] | None = None):
    config = build_default_game_config()
    config.settings.teams = teams or ["Rouges", "Bleus", "Verts"]
    config.settings.buzzer_keys = [str(index + 1) for index in range(len(config.settings.teams))]
    config.settings.total_rounds = 1
    for game in config.games:
        game.enabled = game.game_key == "seven_differences"
    return config.start_session()


def _open_config(*, teams: list[str] | None = None):
    started = _seven_config(teams=teams).start_seven_differences(now_ms=1_000)
    return started.open_seven_differences(now_ms=1_000 + SEVEN_DIFFERENCES_MEMORIZATION_MS)


def test_start_prepares_exactly_seven_secret_differences_and_25_second_deadline() -> None:
    started = _seven_config().start_seven_differences(now_ms=42_000)
    game = started.session.seven_differences

    assert game.phase == "memorizing"
    assert game.reveal_at_ms == 42_000 + 25_000
    assert len(game.differences) == 7
    assert len({difference.id for difference in game.differences}) == 7
    assert game.scores == {"Rouges": 0, "Bleus": 0, "Verts": 0}
    assert game.original_image_url != game.modified_image_url


def test_timer_is_server_authoritative_and_open_is_idempotent() -> None:
    started = _seven_config().start_seven_differences(now_ms=1_000)

    with pytest.raises(InvalidGameConfigError, match="25 secondes"):
        started.open_seven_differences(now_ms=started.session.seven_differences.reveal_at_ms - 1)

    opened = started.open_seven_differences(now_ms=started.session.seven_differences.reveal_at_ms)
    assert opened.session.seven_differences.phase == "open"
    assert opened.open_seven_differences(now_ms=99_999) is opened


def test_correct_answer_keeps_control_then_wrong_answer_blocks_only_that_team() -> None:
    opened = _open_config()
    claimed = opened.register_seven_differences_buzzer("Rouges", now_ms=30_000)
    first_id = claimed.session.seven_differences.differences[0].id
    scored = claimed.find_seven_difference(first_id)

    assert scored.session.seven_differences.phase == "claimed"
    assert scored.session.seven_differences.current_buzzer_team == "Rouges"
    assert scored.session.seven_differences.scores["Rouges"] == 1

    rejected = scored.reject_seven_differences_answer()
    assert rejected.session.seven_differences.phase == "open"
    assert rejected.session.seven_differences.blocked_team == "Rouges"

    with pytest.raises(InvalidGameConfigError, match="attendre"):
        rejected.register_seven_differences_buzzer("Rouges", now_ms=30_001)

    reclaimed = rejected.register_seven_differences_buzzer("Bleus", now_ms=30_002)
    assert reclaimed.session.seven_differences.current_buzzer_team == "Bleus"
    assert reclaimed.session.seven_differences.blocked_team is None


def test_seven_found_differences_finish_round_with_tie_and_round_trip() -> None:
    current = _open_config()
    scoring_order = ["Rouges", "Rouges", "Rouges", "Bleus", "Bleus", "Bleus", "Verts"]

    for index, team in enumerate(scoring_order):
        if current.session.seven_differences.phase == "claimed" and current.session.seven_differences.current_buzzer_team != team:
            current = current.reject_seven_differences_answer()
        if current.session.seven_differences.phase == "open":
            current = current.register_seven_differences_buzzer(team, now_ms=30_000 + index)
        difference_id = current.session.seven_differences.differences[index].id
        current = current.find_seven_difference(difference_id)

    game = current.session.seven_differences
    assert game.phase == "finished"
    assert game.current_buzzer_team is None
    assert game.blocked_team is None
    assert game.winner_team == TIE_LABEL
    assert current.session.active_round and current.session.active_round.completed
    assert current.session.manche_finished is True
    assert current.session.manche_winner == TIE_LABEL

    restored = game_config_from_payload(current.to_dict())
    assert restored.session.seven_differences == game


def test_display_never_receives_secret_labels_or_modified_image_before_reveal() -> None:
    started = _seven_config().start_seven_differences(now_ms=1_000)
    controller = build_client_envelope("game.config.updated", GameConfigReadModel.from_domain(started), "controller")
    display = build_client_envelope("game.config.updated", GameConfigReadModel.from_domain(started), "display")

    controller_game = controller["payload"]["session"]["seven_differences"]
    display_game = display["payload"]["session"]["seven_differences"]
    assert len(controller_game["differences"]) == 7
    assert controller_game["modified_image_url"]
    assert display_game["differences"] == []
    assert display_game["modified_image_url"] == ""
    assert display_game["original_image_url"]

    opened = started.open_seven_differences(started.session.seven_differences.reveal_at_ms)
    revealed = build_client_envelope("game.config.updated", GameConfigReadModel.from_domain(opened), "display")
    assert revealed["payload"]["session"]["seven_differences"]["modified_image_url"]
    assert revealed["payload"]["session"]["seven_differences"]["differences"] == []


class _SlowRepository(GameConfigRepository):
    def __init__(self, current):
        self.current = current

    async def get_current(self):
        await asyncio.sleep(0.01)
        return deepcopy(self.current)

    async def save(self, game_config):
        await asyncio.sleep(0.01)
        self.current = deepcopy(game_config)
        return game_config


def test_concurrent_buzzes_accept_exactly_one_team() -> None:
    repository = _SlowRepository(_open_config(teams=["Rouges", "Bleus"]))
    usecase = SevenDifferencesCommandUseCase(repository)

    async def buzz(team: str):
        return await usecase.register_buzzer(BlindtestBuzzerCommandModel(team=team))

    async def race():
        return await asyncio.gather(buzz("Rouges"), buzz("Bleus"), return_exceptions=True)

    results = asyncio.run(race())
    successes = [result for result in results if not isinstance(result, Exception)]
    failures = [result for result in results if isinstance(result, InvalidGameConfigError)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert repository.current.session.seven_differences.current_buzzer_team in {"Rouges", "Bleus"}


class _DisplayCommands:
    async def open_seven_differences(self):
        return "opened"

    async def register_seven_differences_buzzer(self, payload):
        return f"buzz:{payload.team}"

    async def mark_seven_difference_found(self, payload):
        return f"found:{payload.difference_id}"


def test_display_can_only_open_and_buzz_not_validate_a_difference() -> None:
    commands = _DisplayCommands()
    opened = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="seven-differences.open",
        payload={},
        command_usecase=commands,  # type: ignore[arg-type]
    ))
    buzzed = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="seven-differences.buzzer",
        payload={"team": "Rouges"},
        command_usecase=commands,  # type: ignore[arg-type]
    ))
    forbidden = asyncio.run(dispatch_game_config_event(
        client_type="display",
        event_type="seven-differences.found",
        payload={"difference_id": "score"},
        command_usecase=commands,  # type: ignore[arg-type]
    ))

    assert opened == "opened"
    assert buzzed == "buzz:Rouges"
    assert forbidden == {"type": "error", "detail": "Le client display est en lecture seule."}
