from __future__ import annotations

import json

from application.services.snapshot import serialize_event
from domain.events import (
    AnswerJudged,
    AuctionResolved,
    BidAccepted,
    BombeArmed,
    BombeDieRolling,
    BombeExploded,
    BombePassed,
    BuzzerPressed,
    ChainRecited,
    ChronoStarted,
    ChronoStopped,
    DifferenceFound,
    DomainEvent,
    GameNightFinished,
    GameNightStarted,
    MancheFinished,
    MancheStarted,
    RankingRevealed,
    TeamDisqualified,
    TurnEnded,
    TurnStarted,
    WordFound,
    WordSkipped,
)
from domain.models.game_config import GameConfig
from domain.models.games.forbidden_word import FORBIDDEN_WORD_TURN_MS
from domain.models.games.memory import MEMORY_CHAIN_LENGTH
from domain.models.games.seven_differences import SEVEN_DIFFERENCES_MEMORIZATION_MS
from domain.vo.blindtest_track import build_blindtest_track
from infrastructure.repositories.game_config_mapper import game_config_from_payload
from support import started_config

TWO_TEAMS = ["Rouges", "Bleus"]


def fresh(config: GameConfig) -> GameConfig:
    """Repart d'un agrégat sans événement en attente, comme après un enregistrement."""
    return config.pull_events()[0]


def produced(before: GameConfig, after: GameConfig) -> tuple[DomainEvent, ...]:
    return after.pending_events[len(before.pending_events):]


def _card_word(config: GameConfig) -> str:
    card = config.session.forbidden_word.current_card
    assert card is not None
    return card.word


# --- Orchestration de la soirée


def test_starting_the_night_announces_it_and_the_first_manche() -> None:
    config = started_config("auction")

    assert config.pending_events == (GameNightStarted(total_rounds=1), MancheStarted(number=1, game_key="auction"))


def _finish_forbidden_word_manche(config: GameConfig, scorer: str | None) -> GameConfig:
    """Joue tous les tours ; seule `scorer` fait deviner un mot (aucune si `None` : égalité)."""
    current = config
    for turn_index, team in enumerate(current.session.forbidden_word.turn_order):
        start = 1_000_000 * (turn_index + 1)
        current = current.start_forbidden_word_turn(start)
        if team == scorer:
            card_id = current.session.forbidden_word.current_card.id  # type: ignore[union-attr]
            current = current.resolve_forbidden_word_card(card_id, found=True, now_ms=start + 1)
        current = current.expire_due_deadline(start + FORBIDDEN_WORD_TURN_MS)
    return current


def test_manche_end_next_manche_and_final_ranking_are_announced() -> None:
    config = fresh(started_config("forbidden_word", teams=TWO_TEAMS, total_rounds=2))

    finished = _finish_forbidden_word_manche(config, scorer="Bleus")
    assert finished.pending_events[-1] == MancheFinished(number=1, game_key="forbidden_word", winner="Bleus")

    second = fresh(finished).next_manche()
    assert second.pending_events == (MancheStarted(number=2, game_key="forbidden_word"),)

    ended = fresh(_finish_forbidden_word_manche(fresh(second), scorer="Bleus")).next_manche()
    assert ended.pending_events == (GameNightFinished(leaders=("Bleus",)),)

    last = fresh(ended).reveal_next_ranking()
    winner = fresh(last).reveal_next_ranking()
    assert last.pending_events == (RankingRevealed(team="Rouges", rank=2, manches_won=0),)
    assert winner.pending_events == (RankingRevealed(team="Bleus", rank=1, manches_won=2),)
    assert fresh(winner).reveal_next_ranking().pending_events == ()


def test_a_tie_is_announced_as_such() -> None:
    finished = _finish_forbidden_word_manche(fresh(started_config("forbidden_word", teams=TWO_TEAMS)), scorer=None)

    assert finished.pending_events[-1] == MancheFinished(number=1, game_key="forbidden_word", winner="Égalité")


# --- Événements propres à chaque jeu


def test_forbidden_word_turn_events() -> None:
    ready = fresh(started_config("forbidden_word", teams=TWO_TEAMS))
    team = ready.session.forbidden_word.turn_order[0]

    running = ready.start_forbidden_word_turn(1_000)
    first_word = _card_word(running)
    found = running.resolve_forbidden_word_card(running.session.forbidden_word.current_card.id, found=True, now_ms=2_000)  # type: ignore[union-attr]
    second_word = _card_word(found)
    skipped = found.resolve_forbidden_word_card(found.session.forbidden_word.current_card.id, found=False, now_ms=3_000)  # type: ignore[union-attr]
    stale = skipped.resolve_forbidden_word_card("carte-perimee", found=True, now_ms=3_100)
    ended = skipped.expire_due_deadline(1_000 + FORBIDDEN_WORD_TURN_MS)

    assert produced(ready, running) == (TurnStarted(team),)
    assert produced(running, found) == (WordFound(team, first_word),)
    assert produced(found, skipped) == (WordSkipped(team, second_word),)
    assert stale is skipped
    assert produced(skipped, ended) == (TurnEnded(team, found_count=1),)


def test_blindtest_buzz_and_answer_events() -> None:
    tracks = [build_blindtest_track(title=f"T{i}", artist=f"A{i}", preview_url=f"https://x/{i}.mp3") for i in range(10)]
    loaded = fresh(started_config("blindtest", teams=TWO_TEAMS).with_blindtest_tracks(tracks))

    buzzed = loaded.register_buzzer("Rouges")
    wrong = buzzed.mark_answer(False)
    rebuzzed = wrong.register_buzzer("Bleus")
    right = rebuzzed.mark_answer(True)
    advanced = right.advance_track()

    assert produced(loaded, buzzed) == (BuzzerPressed("blindtest", "Rouges"),)
    assert produced(buzzed, wrong) == (AnswerJudged("blindtest", "Rouges", correct=False),)
    assert produced(wrong, rebuzzed) == (BuzzerPressed("blindtest", "Bleus"),)
    assert produced(rebuzzed, right) == (AnswerJudged("blindtest", "Bleus", correct=True),)
    assert produced(right, advanced) == ()


def test_culture_buzz_and_answer_events() -> None:
    question = fresh(started_config("culture", teams=TWO_TEAMS).start_culture().select_culture_difficulty("facile"))

    buzzed = question.register_culture_buzzer("Bleus")
    wrong = buzzed.answer_culture(False)
    right = wrong.register_culture_buzzer("Rouges").answer_culture(True)

    assert produced(question, buzzed) == (BuzzerPressed("culture", "Bleus"),)
    assert produced(buzzed, wrong) == (AnswerJudged("culture", "Bleus", correct=False),)
    assert produced(wrong, right)[-1] == AnswerJudged("culture", "Rouges", correct=True)


def test_stopchrono_events() -> None:
    idle = fresh(started_config("stopchrono", teams=TWO_TEAMS))
    team = idle.settings.teams[0]

    running = idle.start_chrono(10_000)
    stopped = running.stop_chrono(10_000 + idle.session.stopchrono.target_ms + 250)

    assert produced(idle, running) == (ChronoStarted(team),)
    assert produced(running, stopped) == (ChronoStopped(team, elapsed_ms=idle.session.stopchrono.target_ms + 250, delta_ms=250),)


def test_bombe_events() -> None:
    prepared = fresh(started_config("bombe", teams=TWO_TEAMS).start_bombe(now_ms=1_000))
    roller = prepared.settings.teams[prepared.session.bombe.roller_team_index or 0]
    other = next(team for team in TWO_TEAMS if team != roller)

    rolling = prepared.register_bombe_buzzer(roller, now_ms=1_001)
    armed = rolling.begin_bombe_after_roll(rolling.session.bombe.die_reveal_at_ms)
    passed = armed.register_bombe_buzzer(roller, now_ms=armed.session.bombe.started_at_ms + 1)
    exploded = passed.explode_bombe(passed.session.bombe.deadline_at_ms)

    assert produced(prepared, rolling) == (BombeDieRolling(roller),)
    assert produced(rolling, armed) == (BombeArmed(roller, die_result=armed.session.bombe.die_result),)
    assert produced(armed, passed) == (BombePassed(from_team=roller, to_team=other),)
    assert produced(passed, exploded) == (BombeExploded(other), MancheFinished(1, "bombe", roller))


def test_memory_events() -> None:
    current = fresh(started_config("memory").start_memory())
    for _ in range(MEMORY_CHAIN_LENGTH):
        current = current.next_memory_question()
    reciting_team = current.settings.teams[current.session.memory.current_team_index]

    validated = fresh(current).validate_memory_sequence()
    assert validated.pending_events == (ChainRecited(reciting_team),)

    current = validated
    for _ in range(MEMORY_CHAIN_LENGTH):
        current = current.next_memory_question()
    faulty_team = current.settings.teams[current.session.memory.current_team_index]
    assert fresh(current).disqualify_memory_team().pending_events == (TeamDisqualified(faulty_team),)


def test_seven_differences_events() -> None:
    started = started_config("seven_differences").start_seven_differences(now_ms=1_000)
    opened = fresh(started.open_seven_differences(1_000 + SEVEN_DIFFERENCES_MEMORIZATION_MS))

    claimed = opened.register_seven_differences_buzzer("Rouges", now_ms=30_000)
    rejected = claimed.reject_seven_differences_answer()
    reclaimed = rejected.register_seven_differences_buzzer("Bleus", now_ms=30_001)
    found = reclaimed.find_seven_difference(reclaimed.session.seven_differences.differences[0].id)

    assert produced(opened, claimed) == (BuzzerPressed("seven_differences", "Rouges"),)
    assert produced(claimed, rejected) == (AnswerJudged("seven_differences", "Rouges", correct=False),)
    assert produced(rejected, reclaimed) == (BuzzerPressed("seven_differences", "Bleus"),)
    assert produced(reclaimed, found) == (DifferenceFound("Bleus", remaining=6),)


def test_auction_events() -> None:
    bidding = fresh(started_config("auction").start_auction())

    buzzed = bidding.register_auction_buzzer("Verts", now_ms=100)
    selected = buzzed.select_auction_bid("Verts", 2)
    running = selected.launch_auction_attempt(now_ms=1_000)
    counted = running.change_auction_count(1, 1_001).change_auction_count(1, 1_002)
    resolved = counted.register_auction_buzzer("Verts", now_ms=1_003)

    assert produced(bidding, buzzed) == (BuzzerPressed("auction", "Verts"),)
    assert produced(buzzed, selected) == (BidAccepted("Verts", target_count=2),)
    assert produced(selected, running) == ()
    assert produced(counted, resolved) == (AuctionResolved("Verts", target_count=2, succeeded=True),)


# --- Garanties transverses


def test_events_never_leak_secrets_to_the_public_screen() -> None:
    ready = fresh(started_config("forbidden_word", teams=TWO_TEAMS))
    running = ready.start_forbidden_word_turn(1_000)
    card = running.session.forbidden_word.current_card
    assert card is not None
    public = json.dumps([serialize_event(event) for event in running.pending_events], ensure_ascii=False)
    assert card.word not in public and not any(word in public for word in card.forbidden_words)

    question = fresh(started_config("culture", teams=TWO_TEAMS).start_culture().select_culture_difficulty("facile"))
    judged = question.register_culture_buzzer("Rouges").answer_culture(False)
    answer = question.session.culture.current_question.answer  # type: ignore[union-attr]
    assert answer not in json.dumps([serialize_event(event) for event in judged.pending_events], ensure_ascii=False)

    prepared = fresh(started_config("bombe", teams=TWO_TEAMS).start_bombe(now_ms=1_000))
    roller = prepared.settings.teams[prepared.session.bombe.roller_team_index or 0]
    rolling = prepared.register_bombe_buzzer(roller, now_ms=1_001)
    assert all("die_result" not in serialize_event(event) for event in rolling.pending_events)


def test_events_are_neither_persisted_nor_compared() -> None:
    config = started_config("auction")
    cleared, events = config.pull_events()

    assert events and cleared.pending_events == ()
    assert cleared == config
    assert "pending_events" not in json.dumps(config.to_dict())
    assert game_config_from_payload(config.to_dict()).pending_events == ()


def test_serialized_events_carry_their_type_and_fields() -> None:
    assert serialize_event(WordFound("Rouges", "Paris")) == {"type": "forbidden_word.word_found", "team": "Rouges", "word": "Paris"}
