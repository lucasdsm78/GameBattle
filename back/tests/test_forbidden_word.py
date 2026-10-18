from __future__ import annotations

import asyncio
from dataclasses import replace
import re
import unicodedata

import pytest
from pydantic import ValidationError

from application.forbidden_word import ForbiddenWordCommandUseCase
from application.game_config.game_config_models import ForbiddenWordCardCommandModel, GameConfigReadModel
from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.forbidden_word_catalog import FORBIDDEN_WORD_CARDS
from domain.game_config.model.game_config import (
    FORBIDDEN_WORD_TURN_MS,
    TIE_LABEL,
    ForbiddenWordTurn,
    GameConfig,
    build_default_game_config,
)
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.game_config_payload_mapper import game_config_from_payload
from presentation.realtime.game_config_ws_handler import build_client_envelope, dispatch_game_config_event

TEAMS = ["Rouges", "Bleus", "Verts"]


def _forbidden_word_config(teams: list[str] | None = None) -> GameConfig:
    config = build_default_game_config()
    config.settings.teams = teams or list(TEAMS)
    config.settings.buzzer_keys = [str(index + 1) for index in range(len(config.settings.teams))]
    config.settings.total_rounds = 1
    for game in config.games:
        game.enabled = game.game_key == "forbidden_word"
    return config.start_session()


def _running(now_ms: int = 1_000) -> GameConfig:
    return _forbidden_word_config().start_forbidden_word_turn(now_ms)


def _card_id(config: GameConfig) -> str:
    card = config.session.forbidden_word.current_card
    assert card is not None
    return card.id


def _play_turn(config: GameConfig, *, found: int, start_ms: int) -> GameConfig:
    current = config.start_forbidden_word_turn(start_ms)
    for offset in range(found):
        current = current.resolve_forbidden_word_card(_card_id(current), found=True, now_ms=start_ms + offset + 1)
    return current.expire_due_deadline(start_ms + FORBIDDEN_WORD_TURN_MS)


def test_manche_starts_ready_with_a_random_turn_order_covering_every_team() -> None:
    config = _forbidden_word_config()
    game = config.session.forbidden_word
    assert game.phase == "ready"
    assert sorted(game.turn_order) == sorted(TEAMS)
    assert game.current_team == game.turn_order[0]
    assert game.scores(TEAMS) == {team: 0 for team in TEAMS}
    assert game.current_card is None


def test_start_turn_draws_a_card_and_starts_a_sixty_second_server_timer() -> None:
    running = _running(now_ms=5_000)
    game = running.session.forbidden_word
    assert game.phase == "running"
    assert game.current_team == game.turn_order[0]
    assert game.deadline_at_ms == 5_000 + FORBIDDEN_WORD_TURN_MS
    assert game.current_card is not None
    assert 3 <= len(game.current_card.forbidden_words) <= 5
    assert game.used_card_ids == [game.current_card.id]

    with pytest.raises(InvalidGameConfigError, match="prête"):
        running.start_forbidden_word_turn(6_000)


def test_found_scores_one_point_and_draws_a_fresh_card() -> None:
    running = _running()
    first_card = running.session.forbidden_word.current_card
    assert first_card is not None

    found = running.resolve_forbidden_word_card(first_card.id, found=True, now_ms=2_000)
    game = found.session.forbidden_word
    assert game.turns[-1].found_words == [first_card.word]
    assert game.scores(TEAMS)[game.turn_order[0]] == 1
    assert game.current_card is not None and game.current_card.id != first_card.id
    assert game.used_card_ids == [first_card.id, game.current_card.id]


def test_skip_draws_a_new_card_without_scoring() -> None:
    running = _running()
    first_card = running.session.forbidden_word.current_card
    assert first_card is not None

    skipped = running.resolve_forbidden_word_card(first_card.id, found=False, now_ms=2_000)
    game = skipped.session.forbidden_word
    assert game.turns[-1].skipped_words == [first_card.word]
    assert game.turns[-1].found_words == []
    assert game.scores(TEAMS)[game.turn_order[0]] == 0
    assert game.current_card is not None and game.current_card.id != first_card.id


def test_a_duplicate_press_on_a_stale_card_is_ignored() -> None:
    running = _running()
    stale_id = _card_id(running)
    found = running.resolve_forbidden_word_card(stale_id, found=True, now_ms=2_000)

    assert found.resolve_forbidden_word_card(stale_id, found=True, now_ms=2_100) is found


def test_a_press_arriving_after_the_turn_ended_is_ignored() -> None:
    running = _running(now_ms=1_000)
    card_id = _card_id(running)
    ended = running.expire_due_deadline(1_000 + FORBIDDEN_WORD_TURN_MS)
    assert ended.resolve_forbidden_word_card(card_id, found=True, now_ms=1_000 + FORBIDDEN_WORD_TURN_MS + 50) is ended


def test_a_press_after_the_deadline_closes_the_turn_without_scoring() -> None:
    running = _running(now_ms=1_000)
    late = running.resolve_forbidden_word_card(_card_id(running), found=True, now_ms=1_000 + FORBIDDEN_WORD_TURN_MS)
    game = late.session.forbidden_word
    assert game.phase == "ready"
    assert game.turns[0].found_words == []
    assert game.current_card is None


def test_deadline_hands_over_to_the_next_team_then_finishes_the_manche() -> None:
    config = _forbidden_word_config()
    order = config.session.forbidden_word.turn_order
    running = config.start_forbidden_word_turn(1_000)

    assert running.expire_due_deadline(1_000 + FORBIDDEN_WORD_TURN_MS - 1) is running

    current = running.expire_due_deadline(1_000 + FORBIDDEN_WORD_TURN_MS)
    assert current.session.forbidden_word.phase == "ready"
    assert current.session.forbidden_word.current_team == order[1]
    assert current.session.manche_finished is False

    current = _play_turn(current, found=4, start_ms=100_000)
    current = _play_turn(current, found=2, start_ms=200_000)
    game = current.session.forbidden_word
    assert game.phase == "finished"
    assert game.scores(TEAMS) == {order[0]: 0, order[1]: 4, order[2]: 2}
    assert game.winner_team == order[1]
    assert current.session.manche_finished is True
    assert current.session.manche_winner == order[1]
    assert current.session.active_round is not None and current.session.active_round.completed
    assert current.expire_due_deadline(10**12) is current


def test_equal_best_scores_end_in_a_tie() -> None:
    current = _forbidden_word_config(teams=["Rouges", "Bleus"])
    current = _play_turn(current, found=3, start_ms=1_000)
    current = _play_turn(current, found=3, start_ms=100_000)
    assert current.session.forbidden_word.winner_team == TIE_LABEL
    assert current.session.manche_winner == TIE_LABEL


def test_draws_restart_a_cycle_when_the_catalog_is_exhausted() -> None:
    running = _running()
    game = running.session.forbidden_word
    every_id = [card.id for card in FORBIDDEN_WORD_CARDS]
    exhausted = running._replace_session(forbidden_word=replace(game, used_card_ids=every_id))
    current_id = _card_id(exhausted)

    next_card = exhausted.resolve_forbidden_word_card(current_id, found=True, now_ms=2_000)
    next_game = next_card.session.forbidden_word
    assert next_game.current_card is not None
    assert next_game.used_card_ids == [next_game.current_card.id]
    next_card.validate()


def test_tampered_states_are_rejected() -> None:
    running = _running()
    game = running.session.forbidden_word
    wrong_team = replace(game, turns=[ForbiddenWordTurn(team=game.turn_order[1])])
    with pytest.raises(InvalidGameConfigError, match="ordre de passage"):
        running._replace_session(forbidden_word=wrong_team).validate()
    longer_turn = replace(game, deadline_at_ms=game.deadline_at_ms + 30_000)
    with pytest.raises(InvalidGameConfigError, match="tour en cours"):
        running._replace_session(forbidden_word=longer_turn).validate()
    fake_winner = replace(game, phase="finished", current_card=None, winner_team=game.turn_order[0])
    with pytest.raises(InvalidGameConfigError, match="fin de manche"):
        running._replace_session(forbidden_word=fake_winner).validate()


def test_persistence_round_trip() -> None:
    running = _running()
    running = running.resolve_forbidden_word_card(_card_id(running), found=True, now_ms=2_000)
    restored = game_config_from_payload(running.to_dict())
    assert restored.session.forbidden_word == running.session.forbidden_word


def test_display_never_receives_the_secret_card() -> None:
    model = GameConfigReadModel.from_domain(_running())
    controller = build_client_envelope("game.config.updated", model, "controller")["payload"]["session"]["forbidden_word"]
    display = build_client_envelope("game.config.updated", model, "display")["payload"]["session"]["forbidden_word"]

    assert controller["current_card"]["word"]
    assert len(controller["current_card"]["forbidden_words"]) >= 3
    assert display["current_card"] is None
    assert "used_card_ids" not in controller and "used_card_ids" not in display
    assert display["current_team"] == controller["current_team"]
    assert display["turn_duration_ms"] == FORBIDDEN_WORD_TURN_MS


@pytest.mark.parametrize("event_type", ["forbidden-word.start-turn", "forbidden-word.found", "forbidden-word.skip"])
def test_display_cannot_drive_the_game(event_type: str) -> None:
    result = asyncio.run(dispatch_game_config_event(
        client_type="display", event_type=event_type, payload={"card_id": "paris"}, command_usecase=object()  # type: ignore[arg-type]
    ))
    assert result == {"type": "error", "detail": "Le client display est en lecture seule."}


@pytest.mark.parametrize("card_id", ["", "Paris", "../etc", "<script>", "a" * 61])
def test_card_command_rejects_malformed_identifiers(card_id: str) -> None:
    with pytest.raises(ValidationError):
        ForbiddenWordCardCommandModel(card_id=card_id)


class _InMemoryRepository(GameConfigRepository):
    def __init__(self, config: GameConfig) -> None:
        self.config = config
        self.saves = 0

    async def get_current(self) -> GameConfig:
        return self.config

    async def save(self, game_config: GameConfig) -> GameConfig:
        self.saves += 1
        self.config = game_config
        return game_config


def test_use_case_does_not_persist_or_broadcast_a_duplicate_press() -> None:
    repository = _InMemoryRepository(_forbidden_word_config().start_forbidden_word_turn(ForbiddenWordCommandUseCase._now_ms()))
    usecase = ForbiddenWordCommandUseCase(repository)
    payload = ForbiddenWordCardCommandModel(card_id=_card_id(repository.config))

    async def press_twice() -> tuple[object, object]:
        return await usecase.mark_found(payload), await usecase.mark_found(payload)

    first, second = asyncio.run(press_twice())
    assert isinstance(first, GameConfigReadModel)
    assert second is None
    assert repository.saves == 1


def _normalize_tokens(value: str) -> set[str]:
    ascii_value = unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode("ascii")
    return set(re.split(r"[^a-z0-9]+", ascii_value)) - {""}


def test_catalog_is_large_unique_and_well_formed() -> None:
    assert len(FORBIDDEN_WORD_CARDS) >= 200
    assert len({card.id for card in FORBIDDEN_WORD_CARDS}) == len(FORBIDDEN_WORD_CARDS)
    assert len({card.word.casefold() for card in FORBIDDEN_WORD_CARDS}) == len(FORBIDDEN_WORD_CARDS)
    for card in FORBIDDEN_WORD_CARDS:
        ForbiddenWordCardCommandModel(card_id=card.id)
        assert 3 <= len(card.forbidden_words) <= 5, card
        assert len({word.casefold() for word in card.forbidden_words}) == len(card.forbidden_words), card
        word_tokens = _normalize_tokens(card.word)
        for forbidden in card.forbidden_words:
            assert forbidden.strip(), card
            assert not _normalize_tokens(forbidden) & word_tokens, (card.word, forbidden)
