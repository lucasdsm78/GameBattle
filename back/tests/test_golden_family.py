from __future__ import annotations

import asyncio
import unicodedata
from dataclasses import replace

import pytest

from application.game_night.game_config_presenter import present_game_config
from application.shared.commands import TeamCommand
from application.shared.snapshot import ClientRole
from domain.golden_family.events import (
    FamilyAnswerRevealed,
    FamilyBoardRevealed,
    FamilyControlTaken,
    FamilyQuestionShown,
    FamilyStrikeGiven,
)
from domain.golden_family.models.family_question import BoardSlot
from domain.golden_family.models.golden_family_state import GOLDEN_FAMILY_WINNING_SCORE
from domain.golden_family.services.golden_family_catalog import (
    FAMILY_QUESTIONS,
    FAMILY_QUESTIONS_BY_ID,
)
from domain.shared.events import AnswerJudged, BuzzerPressed
from exceptions import CommandNotAllowedError, InvalidGameConfigError
from infrastructure.repositories.game_config_mapper import (
    game_config_from_payload,
    game_config_to_payload,
)
from support import GameHarness, started_config

TEAMS = ["Rouges", "Bleus", "Verts"]
# Se laver 45 · Chanter 20 · Réfléchir 18 · Se raser 9 · Pleurer 6
DOUCHE = FAMILY_QUESTIONS_BY_ID["douche"]
WASH, SING, THINK, SHAVE, CRY = range(5)


def _faceoff(teams: list[str] | None = None, *, scores: dict[str, int] | None = None):
    """La question « douche » à l'écran, buzzers ouverts."""
    config = started_config("golden_family", teams=teams or TEAMS).pull_events()[0].show_next_family_question()
    game = config.session.golden_family
    rigged = replace(
        game, question=DOUCHE, board=[BoardSlot() for _ in DOUCHE.answers], used_questions=[DOUCHE.id],
        scores=scores or game.scores,
    )
    return config._replace_session(golden_family=rigged)


def _game(config):
    return config.session.golden_family


def _answer(config, index: int):
    return config.give_family_answer(index, _game(config).turn)


def _strike(config):
    return config.strike_family_answer(_game(config).turn)


def _produced(before, after):
    return after.pending_events[len(before.pending_events):]


def _control(team: str = "Rouges"):
    """`team` a buzzé et trouvé la réponse la plus citée : elle a la main."""
    return _answer(_faceoff().register_golden_family_buzzer(team, 0), WASH)


def test_a_question_opens_the_face_off_and_hides_the_board_from_the_public_screen() -> None:
    config = _faceoff()
    game = _game(config)
    assert game.phase == "faceoff" and game.question_number == 1 and game.current_team is None

    controller, display = present_game_config(config)
    controller_game, display_game = controller["session"]["golden_family"], display["session"]["golden_family"]
    assert controller_game["question"]["answers"][0] == {"text": "Se laver", "points": 45}
    assert display_game["question"]["text"] == DOUCHE.text
    assert display_game["question"]["answers"] == [{"text": "", "points": 0}] * len(DOUCHE.answers)
    for view in (controller_game, display_game):
        assert "used_questions" not in view and "attempts" not in view
        assert view["winning_score"] == GOLDEN_FAMILY_WINNING_SCORE


def test_the_first_team_to_buzz_answers_first() -> None:
    game = _game(_faceoff().register_golden_family_buzzer("Bleus", 0))

    assert game.phase == "duel" and game.current_team == "Bleus"
    assert game.pending_teams == ["Verts", "Rouges"]
    with pytest.raises(InvalidGameConfigError, match="pas ouverts"):
        _faceoff().register_golden_family_buzzer("Bleus", 0).register_golden_family_buzzer("Rouges", 0)


def test_the_buzzer_with_the_top_answer_takes_control_immediately() -> None:
    game = _game(_control("Rouges"))

    assert game.phase == "control" and game.control_team == game.current_team == "Rouges"
    assert game.scores == {"Rouges": 45, "Bleus": 0, "Verts": 0}
    assert game.board[WASH] == BoardSlot(revealed=True, found_by="Rouges")


def test_otherwise_every_team_answers_and_the_best_answer_takes_control() -> None:
    duel = _answer(_faceoff().register_golden_family_buzzer("Rouges", 0), THINK)
    assert _game(duel).phase == "duel" and _game(duel).current_team == "Bleus"

    duel = _answer(duel, SING)
    assert _game(duel).current_team == "Verts"

    game = _game(_strike(duel))
    assert game.phase == "control" and game.control_team == "Bleus" and game.strikes == 0
    assert game.scores == {"Rouges": 18, "Bleus": 20, "Verts": 0}


def test_the_buzzers_reopen_when_nobody_finds_an_answer_in_the_face_off() -> None:
    current = _faceoff().register_golden_family_buzzer("Verts", 0)
    for _ in TEAMS:
        current = _strike(current)

    game = _game(current)
    assert game.phase == "faceoff" and game.current_team is None and game.attempts == []
    assert game.strikes == 0 and game.misses == 3


def test_the_team_in_control_scores_each_answer_it_finds() -> None:
    game = _game(_answer(_control("Rouges"), SHAVE))

    assert game.phase == "control" and game.scores["Rouges"] == 45 + 9


def test_three_strikes_let_each_other_team_try_once_and_the_best_takes_control() -> None:
    current = _control("Rouges")
    current = _strike(_strike(current))
    assert _game(current).strikes == 2 and _game(current).phase == "control"

    stolen = _strike(current)
    game = _game(stolen)
    assert game.phase == "steal" and game.strikes == 3 and game.steal_from == "Rouges"
    assert game.current_team == "Bleus" and game.pending_teams == ["Verts"]

    current = _answer(_answer(stolen, CRY), SING)
    game = _game(current)
    assert game.phase == "control" and game.control_team == "Verts" and game.strikes == 0
    assert game.scores == {"Rouges": 45, "Bleus": 6, "Verts": 20}


def test_when_every_thief_fails_control_goes_back_and_forth_until_a_right_answer() -> None:
    current = _strike(_strike(_strike(_control("Rouges"))))
    current = _strike(_strike(current))  # Bleus puis Verts échouent
    game = _game(current)
    assert game.phase == "steal" and game.current_team == "Rouges" and game.pending_teams == []

    current = _strike(current)  # Rouges échoue aussi : les autres retentent
    assert _game(current).current_team == "Bleus" and _game(current).pending_teams == ["Verts"]

    current = _answer(_strike(current), SHAVE)
    game = _game(current)
    assert game.phase == "control" and game.control_team == "Verts" and game.scores["Verts"] == 9


def test_the_question_ends_when_the_board_is_complete_then_a_new_one_starts() -> None:
    current = _control("Rouges")
    for index in (SING, THINK, SHAVE, CRY):
        current = _answer(current, index)

    game = _game(current)
    assert game.phase == "revealed" and game.scores["Rouges"] == 98
    assert all(slot.found_by == "Rouges" for slot in game.board)

    following = _game(current.show_next_family_question())
    assert following.phase == "faceoff" and following.question_number == 2
    assert following.question.id != DOUCHE.id and following.scores["Rouges"] == 98


def test_the_presenter_can_reveal_the_remaining_answers_without_points() -> None:
    revealed = _control("Rouges").reveal_family_board()
    game = _game(revealed)

    assert game.phase == "revealed" and all(slot.revealed for slot in game.board)
    assert [slot.found_by for slot in game.board] == ["Rouges", None, None, None, None]
    assert game.scores["Rouges"] == 45
    assert present_game_config(revealed)[1]["session"]["golden_family"]["question"]["answers"][1]["text"] == "Chanter"
    with pytest.raises(InvalidGameConfigError, match="Aucune question"):
        revealed.reveal_family_board()


def test_the_first_team_to_three_hundred_wins_and_the_board_is_revealed() -> None:
    near_win = _faceoff(scores={"Rouges": 290, "Bleus": 0, "Verts": 0}).register_golden_family_buzzer("Rouges", 0)
    finished = _answer(near_win, WASH)
    game = _game(finished)

    assert game.phase == "finished" and game.winner_team == "Rouges" and game.scores["Rouges"] == 335
    assert all(slot.revealed for slot in game.board)
    assert finished.session.manche_winner == "Rouges"


def test_presenter_decisions_are_idempotent() -> None:
    control = _control("Rouges")
    stale_turn = _game(control).turn - 1

    assert control.strike_family_answer(stale_turn) is control
    assert control.give_family_answer(SHAVE, stale_turn) is control
    once = _strike(control)
    assert once.strike_family_answer(_game(control).turn) is once


def test_invalid_presenter_decisions_are_rejected() -> None:
    control = _control("Rouges")
    with pytest.raises(InvalidGameConfigError, match="déjà révélée"):
        _answer(control, WASH)
    with pytest.raises(InvalidGameConfigError, match="ne fait pas partie"):
        _answer(control, 7)
    with pytest.raises(InvalidGameConfigError, match="Aucune équipe"):
        _strike(_faceoff())
    with pytest.raises(InvalidGameConfigError, match="déjà en cours"):
        control.show_next_family_question()


def test_domain_events_follow_the_question() -> None:
    ready = started_config("golden_family", teams=TEAMS).pull_events()[0]
    shown = ready.show_next_family_question()
    assert _produced(ready, shown) == (FamilyQuestionShown(1, len(_game(shown).question.answers)),)

    faceoff = _faceoff()
    buzzed = faceoff.register_golden_family_buzzer("Rouges", 0)
    controlled = _answer(buzzed, WASH)
    struck = _strike(_strike(_strike(controlled)))
    assert _produced(faceoff, buzzed) == (BuzzerPressed("golden_family", "Rouges"),)
    assert _produced(buzzed, controlled) == (
        AnswerJudged("golden_family", "Rouges", correct=True),
        FamilyAnswerRevealed("Se laver", 45, "Rouges"),
        FamilyControlTaken("Rouges"),
    )
    assert _produced(_strike(_strike(controlled)), struck) == (
        AnswerJudged("golden_family", "Rouges", correct=False),
        FamilyStrikeGiven("Rouges", 3),
    )
    assert FamilyBoardRevealed(1) in controlled.reveal_family_board().pending_events


def test_events_never_leak_hidden_answers() -> None:
    struck = _strike(_strike(_strike(_control("Rouges"))))

    hidden = [answer.text for answer in DOUCHE.answers[1:]]
    assert not any(text in repr(struck.pending_events) for text in hidden)


def test_persistence_round_trip() -> None:
    stealing = _strike(_strike(_strike(_control("Rouges"))))

    assert game_config_from_payload(game_config_to_payload(stealing)).session.golden_family == _game(stealing)


def test_tampered_states_are_rejected() -> None:
    control = _control("Rouges")
    game = _game(control)
    forged = replace(DOUCHE, answers=[replace(DOUCHE.answers[0], points=99), *DOUCHE.answers[1:]])

    for tampered, message in (
        (replace(game, question=forged), "question"),
        (replace(game, board=game.board[:-1]), "tableau"),
        (replace(game, board=[BoardSlot(revealed=False, found_by="Rouges"), *game.board[1:]]), "tableau"),
        (replace(game, strikes=4), "fautes"),
        (replace(game, current_team="Bleus"), "main"),
        (replace(game, current_team=None), "répond"),
        (replace(game, scores={**game.scores, "Rouges": -5}), "scores"),
    ):
        with pytest.raises(InvalidGameConfigError, match=message):
            control._replace_session(golden_family=tampered).validate()


def test_display_buzzes_but_only_the_presenter_judges() -> None:
    harness = GameHarness(_faceoff())

    harness.run("golden-family.buzzer", {"team": "Verts"}, role=ClientRole.DISPLAY)
    assert _game(harness.config).current_team == "Verts"
    for event, payload in (("golden-family.answer", {"answer_index": 0, "turn": 0}), ("golden-family.strike", {"turn": 0})):
        with pytest.raises(CommandNotAllowedError, match="lecture seule"):
            harness.run(event, payload, role=ClientRole.DISPLAY)

    snapshot = harness.run("golden-family.answer", {"answer_index": WASH, "turn": 0})
    assert _game(harness.config).control_team == "Verts"
    assert [event["type"] for event in snapshot.events] == [
        "answer.judged", "golden_family.answer_revealed", "golden_family.control_taken",
    ]


def test_a_hardware_buzzer_opens_the_duel() -> None:
    harness = GameHarness(_faceoff())

    asyncio.run(harness.use_cases.game_night.register_hardware_buzzer(TeamCommand(team="Bleus")))

    assert _game(harness.config).current_team == "Bleus"


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text.casefold()).encode("ascii", "ignore").decode("ascii")


def test_catalog_is_large_and_well_formed() -> None:
    assert len(FAMILY_QUESTIONS) >= 60
    assert len(FAMILY_QUESTIONS_BY_ID) == len(FAMILY_QUESTIONS)
    for question in FAMILY_QUESTIONS:
        points = [answer.points for answer in question.answers]
        assert 5 <= len(question.answers) <= 8, question.id
        assert all(value > 0 for value in points) and sum(points) <= 100, question.id
        assert points == sorted(points, reverse=True), question.id
        assert len({_normalize(answer.text) for answer in question.answers}) == len(question.answers), question.id
        assert all(len(answer.text) <= 28 for answer in question.answers), question.id
        assert question.text.startswith("Citez") and len(question.text) <= 70, question.id
