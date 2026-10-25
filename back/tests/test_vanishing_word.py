from __future__ import annotations

import asyncio
import unicodedata
from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from application.shared.commands import TeamCommand
from application.shared.snapshot import ClientRole
from domain.shared.events import AnswerJudged, BuzzerPressed
from domain.vanishing_word.events import (
    VanishedWordRevealed,
    VanishingListShown,
    WordVanished,
)
from domain.vanishing_word.models.vanishing_word_state import (
    VANISHING_WORD_MEMORIZATION_MS,
    VANISHING_WORD_WINNING_SCORE,
)
from domain.vanishing_word.services.vanishing_word_catalog import (
    VANISHING_WORDS,
    WORDS_PER_LIST,
)
from exceptions import CommandNotAllowedError, InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from support import GameHarness, started_config

TEAMS = ["Rouges", "Bleus", "Verts"]
START_MS = 1_000
VANISH_MS = START_MS + VANISHING_WORD_MEMORIZATION_MS


def _memorizing(teams: list[str] | None = None):
    return started_config("vanishing_word", teams=teams or TEAMS).pull_events()[0].start_vanishing_round(START_MS)


def _vanished(teams: list[str] | None = None):
    return _memorizing(teams).expire_due_deadline(VANISH_MS)


def _produced(before, after):
    return after.pending_events[len(before.pending_events):]


def test_a_round_shows_eight_distinct_words_for_ten_seconds() -> None:
    config = _memorizing()
    game = config.session.vanishing_word

    assert game.phase == "memorizing"
    assert game.round_number == 1
    assert len(game.words) == WORDS_PER_LIST == len(set(game.words))
    assert game.reveal_at_ms == VANISH_MS
    assert game.vanished_word == "" and game.remaining_words == []
    assert game.scores == {team: 0 for team in TEAMS}


def test_the_server_makes_one_word_vanish_when_memorization_ends() -> None:
    memorizing = _memorizing()

    assert memorizing.expire_due_deadline(VANISH_MS - 1) is memorizing

    vanished = memorizing.expire_due_deadline(VANISH_MS).session.vanishing_word
    assert vanished.phase == "vanished"
    assert vanished.vanished_word in vanished.words
    assert len(vanished.remaining_words) == WORDS_PER_LIST - 1
    assert sorted(vanished.remaining_words) == sorted(word for word in vanished.words if word != vanished.vanished_word)


def test_buzzing_is_refused_during_memorization_but_opens_once_time_is_up() -> None:
    memorizing = _memorizing()

    with pytest.raises(InvalidGameConfigError, match="disparaisse"):
        memorizing.register_vanishing_buzzer("Rouges", now_ms=VANISH_MS - 1)

    claimed = memorizing.register_vanishing_buzzer("Rouges", now_ms=VANISH_MS).session.vanishing_word
    assert claimed.phase == "claimed"
    assert claimed.current_buzzer_team == "Rouges"
    assert claimed.vanished_word


def test_the_first_buzz_takes_control() -> None:
    claimed = _vanished().register_vanishing_buzzer("Bleus", now_ms=VANISH_MS + 1)

    with pytest.raises(InvalidGameConfigError, match="pas ouverts"):
        claimed.register_vanishing_buzzer("Rouges", now_ms=VANISH_MS + 2)


def test_trouve_scores_one_point_and_reveals_the_word() -> None:
    claimed = _vanished().register_vanishing_buzzer("Verts", now_ms=VANISH_MS + 1)

    revealed = claimed.judge_vanishing_word(True).session.vanishing_word

    assert revealed.phase == "revealed"
    assert revealed.scores == {"Rouges": 0, "Bleus": 0, "Verts": 1}
    assert revealed.round_winner == "Verts"
    assert revealed.current_buzzer_team is None


def test_a_wrong_answer_reopens_the_buzzers_for_the_other_teams_only() -> None:
    claimed = _vanished().register_vanishing_buzzer("Rouges", now_ms=VANISH_MS + 1)

    reopened = claimed.judge_vanishing_word(False)
    game = reopened.session.vanishing_word
    assert game.phase == "vanished"
    assert game.excluded_teams == ["Rouges"]
    assert game.scores["Rouges"] == 0

    with pytest.raises(InvalidGameConfigError, match="déjà trompée"):
        reopened.register_vanishing_buzzer("Rouges", now_ms=VANISH_MS + 2)
    assert reopened.register_vanishing_buzzer("Bleus", now_ms=VANISH_MS + 2).session.vanishing_word.current_buzzer_team == "Bleus"


def test_the_word_is_revealed_without_point_when_every_team_failed() -> None:
    current = _vanished(teams=["Rouges", "Bleus"])
    for team in ("Rouges", "Bleus"):
        current = current.register_vanishing_buzzer(team, now_ms=VANISH_MS + 1).judge_vanishing_word(False)

    game = current.session.vanishing_word
    assert game.phase == "revealed"
    assert game.round_winner is None
    assert game.scores == {"Rouges": 0, "Bleus": 0}


def test_the_presenter_can_reveal_the_word_without_awarding_a_point() -> None:
    revealed = _vanished().reveal_vanishing_word().session.vanishing_word

    assert revealed.phase == "revealed"
    assert revealed.round_winner is None
    with pytest.raises(InvalidGameConfigError, match="Aucun mot"):
        _memorizing().reveal_vanishing_word()


def test_the_next_list_never_reuses_a_word_of_the_manche() -> None:
    first = _vanished().reveal_vanishing_word()
    second = first.start_vanishing_round(100_000)

    first_words = set(first.session.vanishing_word.words)
    second_game = second.session.vanishing_word
    assert second_game.round_number == 2
    assert first_words.isdisjoint(second_game.words)
    assert second_game.excluded_teams == [] and second_game.round_winner is None

    with pytest.raises(InvalidGameConfigError, match="déjà en cours"):
        second.start_vanishing_round(100_001)


def test_the_first_team_to_find_five_words_wins_the_manche() -> None:
    current = started_config("vanishing_word", teams=TEAMS)
    for round_index in range(VANISHING_WORD_WINNING_SCORE):
        start = 1_000_000 * (round_index + 1)
        current = current.start_vanishing_round(start).register_vanishing_buzzer("Bleus", now_ms=start + VANISHING_WORD_MEMORIZATION_MS)
        current = current.judge_vanishing_word(True)

    game = current.session.vanishing_word
    assert game.phase == "finished"
    assert game.winner_team == "Bleus"
    assert game.scores["Bleus"] == VANISHING_WORD_WINNING_SCORE
    assert current.session.manche_finished is True
    assert current.session.manche_winner == "Bleus"
    with pytest.raises(InvalidGameConfigError, match="déjà en cours"):
        current.start_vanishing_round(99_000_000)


def test_the_public_screen_never_sees_the_vanished_word_before_the_reveal() -> None:
    memorizing = _memorizing()
    _, display = present_game_config(memorizing)
    assert display["session"]["vanishing_word"]["words"] == memorizing.session.vanishing_word.words

    claimed = memorizing.expire_due_deadline(VANISH_MS).register_vanishing_buzzer("Rouges", now_ms=VANISH_MS + 1)
    controller, display = present_game_config(claimed)
    hidden = display["session"]["vanishing_word"]
    vanished_word = claimed.session.vanishing_word.vanished_word
    assert controller["session"]["vanishing_word"]["vanished_word"] == vanished_word
    assert hidden["vanished_word"] == "" and hidden["words"] == []
    assert vanished_word not in hidden["remaining_words"]
    assert "used_words" not in hidden and "used_words" not in controller["session"]["vanishing_word"]

    _, revealed = present_game_config(claimed.judge_vanishing_word(True))
    assert revealed["session"]["vanishing_word"]["vanished_word"] == vanished_word


def test_domain_events_follow_the_round() -> None:
    ready = started_config("vanishing_word", teams=TEAMS).pull_events()[0]
    memorizing = ready.start_vanishing_round(START_MS)
    vanished = memorizing.expire_due_deadline(VANISH_MS)
    claimed = vanished.register_vanishing_buzzer("Rouges", now_ms=VANISH_MS + 1)
    wrong = claimed.judge_vanishing_word(False)
    reclaimed = wrong.register_vanishing_buzzer("Verts", now_ms=VANISH_MS + 2)
    found = reclaimed.judge_vanishing_word(True)
    word = found.session.vanishing_word.vanished_word

    assert _produced(ready, memorizing) == (VanishingListShown(1),)
    assert _produced(memorizing, vanished) == (WordVanished(1),)
    assert _produced(vanished, claimed) == (BuzzerPressed("vanishing_word", "Rouges"),)
    assert _produced(claimed, wrong) == (AnswerJudged("vanishing_word", "Rouges", correct=False),)
    assert _produced(reclaimed, found) == (
        AnswerJudged("vanishing_word", "Verts", correct=True),
        VanishedWordRevealed(word, found_by="Verts"),
    )
    late_buzz = memorizing.register_vanishing_buzzer("Bleus", now_ms=VANISH_MS)
    assert _produced(memorizing, late_buzz) == (WordVanished(1), BuzzerPressed("vanishing_word", "Bleus"))


def test_persistence_round_trip() -> None:
    claimed = _vanished().register_vanishing_buzzer("Rouges", now_ms=VANISH_MS + 1).judge_vanishing_word(False)

    assert game_config_from_payload(game_config_to_payload(claimed)).session.vanishing_word == claimed.session.vanishing_word


def test_tampered_states_are_rejected() -> None:
    claimed = _vanished().register_vanishing_buzzer("Rouges", now_ms=VANISH_MS + 1)
    game = claimed.session.vanishing_word

    for tampered, message in (
        (replace(game, vanished_word="Inventé"), "incohérent"),
        (replace(game, scores={**game.scores, "Rouges": 3}), "total des scores"),
        (replace(game, phase="finished", current_buzzer_team=None, winner_team="Rouges"), "5 mots"),
    ):
        with pytest.raises(InvalidGameConfigError, match=message):
            claimed._replace_session(vanishing_word=tampered).validate()


def test_display_buzzes_through_websocket_but_cannot_judge() -> None:
    harness = GameHarness(_vanished(), now_ms=VANISH_MS + 5)

    harness.run("vanishing-word.buzzer", {"team": "Rouges"}, role=ClientRole.DISPLAY)
    with pytest.raises(CommandNotAllowedError, match="lecture seule"):
        harness.run("vanishing-word.answer", {"is_correct": True}, role=ClientRole.DISPLAY)

    snapshot = harness.run("vanishing-word.answer", {"is_correct": True})
    assert harness.config.session.vanishing_word.scores["Rouges"] == 1
    assert [event["type"] for event in snapshot.events] == ["answer.judged", "vanishing_word.word_revealed"]


def test_the_deadline_worker_makes_the_word_vanish() -> None:
    clock = {"now": START_MS}
    harness = GameHarness(_memorizing(), now_ms=lambda: clock["now"])

    assert asyncio.run(harness.use_cases.game_night.expire_due_deadlines()) is None
    clock["now"] = VANISH_MS
    snapshot = asyncio.run(harness.use_cases.game_night.expire_due_deadlines())

    assert snapshot is not None
    assert snapshot.display["session"]["vanishing_word"]["phase"] == "vanished"
    assert snapshot.display["session"]["vanishing_word"]["vanished_word"] == ""
    assert [event["type"] for event in snapshot.events] == ["vanishing_word.word_vanished"]


def test_a_hardware_buzzer_claims_the_hand() -> None:
    harness = GameHarness(_vanished(), now_ms=VANISH_MS + 5)

    asyncio.run(harness.use_cases.game_night.register_hardware_buzzer(TeamCommand(team="Verts")))

    assert harness.config.session.vanishing_word.current_buzzer_team == "Verts"


def _normalize(word: str) -> str:
    return unicodedata.normalize("NFKD", word.casefold()).encode("ascii", "ignore").decode("ascii")


def test_catalog_is_large_unique_and_clean() -> None:
    assert len(VANISHING_WORDS) >= 150
    assert len({_normalize(word) for word in VANISHING_WORDS}) == len(VANISHING_WORDS)
    assert all(word.strip() == word and 2 <= len(word) <= 20 for word in VANISHING_WORDS)
