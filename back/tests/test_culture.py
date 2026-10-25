from __future__ import annotations

from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from application.shared.snapshot import ClientRole
from domain.culture.events import CultureAnswerRevealed, CultureTiebreakStarted
from domain.culture.models.culture_state import CULTURE_QUESTIONS_PER_ROUND
from domain.shared.events import AnswerJudged
from exceptions import CommandNotAllowedError, InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from support import GameHarness, started_config

TEAMS = ["Rouges", "Bleus", "Verts"]


def _question(teams: list[str] | None = None):
    return started_config("culture", teams=teams or TEAMS).pull_events()[0].start_culture().select_culture_difficulty("facile")


def _game(config):
    return config.session.culture


def _produced(before, after):
    return after.pending_events[len(before.pending_events):]


def _last_question(scores: dict[str, int]):
    """La dernière question de la manche, affichée, avec les scores donnés."""
    config = _question()
    game = replace(_game(config), current_index=CULTURE_QUESTIONS_PER_ROUND, scores=scores)
    return config._replace_session(culture=game)


def test_the_presenter_reveals_the_answer_without_awarding_a_point() -> None:
    question = _question().register_culture_buzzer("Rouges")
    revealed = question.reveal_culture_answer()
    game = _game(revealed)

    assert game.answered and game.current_buzzer_team is None
    assert game.scores == {team: 0 for team in TEAMS}
    assert _produced(question, revealed) == (CultureAnswerRevealed(1),)
    assert present_game_config(revealed)[1]["session"]["culture"]["current_question"]["answer"] == game.current_question.answer

    with pytest.raises(InvalidGameConfigError, match="déjà révélée"):
        revealed.reveal_culture_answer()
    with pytest.raises(InvalidGameConfigError, match="déjà été validée"):
        revealed.register_culture_buzzer("Bleus")
    assert _game(revealed.next_culture_question()).phase == "selecting"


def test_a_revealed_answer_unblocks_the_next_question() -> None:
    with pytest.raises(InvalidGameConfigError, match="révèle la réponse"):
        _question().next_culture_question()

    assert _game(_question().reveal_culture_answer().next_culture_question()).current_index == 2


def test_a_single_leader_wins_after_the_last_question() -> None:
    finished = _game(_last_question({"Rouges": 4, "Bleus": 3, "Verts": 1}).reveal_culture_answer().next_culture_question())

    assert finished.phase == "finished" and finished.winner_team == "Rouges" and finished.tiebreak_teams == []


def test_tied_leaders_play_a_difficult_tiebreak_question() -> None:
    last = _last_question({"Rouges": 4, "Bleus": 4, "Verts": 1}).reveal_culture_answer()
    tiebreak = last.next_culture_question()
    game = _game(tiebreak)

    assert game.phase == "selecting" and game.tiebreak_teams == ["Rouges", "Bleus"]
    assert game.current_index == CULTURE_QUESTIONS_PER_ROUND + 1 and game.winner_team is None
    assert _produced(last, tiebreak) == (CultureTiebreakStarted(("Rouges", "Bleus")),)

    with pytest.raises(InvalidGameConfigError, match="toujours difficile"):
        tiebreak.select_culture_difficulty("facile")
    question = tiebreak.select_culture_difficulty("difficile")
    assert _game(question).current_question.difficulty == "difficile"
    with pytest.raises(InvalidGameConfigError, match="à égalité"):
        question.register_culture_buzzer("Verts")


def test_the_first_right_answer_of_the_tiebreak_wins_the_manche() -> None:
    question = _last_question({"Rouges": 4, "Bleus": 4, "Verts": 4}).reveal_culture_answer().next_culture_question()
    question = question.select_culture_difficulty("difficile")

    wrong = question.register_culture_buzzer("Verts").answer_culture(False)
    assert _game(wrong).phase == "question" and _game(wrong).current_buzzer_team is None

    won = wrong.register_culture_buzzer("Bleus").answer_culture(True)
    game = _game(won)
    assert game.phase == "finished" and game.winner_team == "Bleus" and game.scores["Bleus"] == 5
    assert won.session.manche_finished and won.session.manche_winner == "Bleus"
    assert AnswerJudged("culture", "Bleus", correct=True) in _produced(wrong, won)


def test_a_tiebreak_nobody_finds_is_followed_by_another_one() -> None:
    question = _last_question({"Rouges": 2, "Bleus": 2, "Verts": 0}).reveal_culture_answer().next_culture_question()
    replay = _game(question.select_culture_difficulty("difficile").reveal_culture_answer().next_culture_question())

    assert replay.phase == "selecting" and replay.tiebreak_teams == ["Rouges", "Bleus"]
    assert replay.current_index == CULTURE_QUESTIONS_PER_ROUND + 2


def test_tampered_tiebreaks_are_rejected() -> None:
    question = _question()
    game = _game(question)

    for tampered in (
        replace(game, tiebreak_teams=["Rouges"]),
        replace(game, tiebreak_teams=["Rouges", "Rouges"]),
        replace(game, tiebreak_teams=["Rouges", "Jaunes"]),
        replace(game, tiebreak_teams=["Rouges", "Bleus"], current_buzzer_team="Verts"),
    ):
        with pytest.raises(InvalidGameConfigError, match="départage|égalité"):
            question._replace_session(culture=tampered).validate()


def test_persistence_round_trip_keeps_the_tiebreak() -> None:
    tiebreak = _last_question({"Rouges": 1, "Bleus": 1, "Verts": 1}).reveal_culture_answer().next_culture_question()

    assert game_config_from_payload(game_config_to_payload(tiebreak)).session.culture == _game(tiebreak)


def test_only_the_presenter_can_reveal_the_answer() -> None:
    harness = GameHarness(_question())

    with pytest.raises(CommandNotAllowedError, match="lecture seule"):
        harness.run("culture.reveal-answer", role=ClientRole.DISPLAY)
    snapshot = harness.run("culture.reveal-answer")
    assert [event["type"] for event in snapshot.events] == ["culture.answer_revealed"]
