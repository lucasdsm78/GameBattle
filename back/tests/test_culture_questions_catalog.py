from __future__ import annotations

from collections import Counter

from domain.game_config.model.culture_questions import (
    CULTURE_DIFFICULTIES,
    CULTURE_QUESTIONS,
    pick_one_culture_question,
)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def test_culture_catalog_is_large_balanced_and_well_formed() -> None:
    assert len(CULTURE_QUESTIONS) >= 570

    counts = Counter(question["difficulty"] for question in CULTURE_QUESTIONS)
    assert set(counts) == CULTURE_DIFFICULTIES
    assert all(counts[difficulty] >= 100 for difficulty in CULTURE_DIFFICULTIES)

    for question in CULTURE_QUESTIONS:
        assert set(question) == {"question", "answer", "explanation", "difficulty"}
        assert all(isinstance(value, str) and value.strip() for value in question.values())
        assert question["difficulty"] in CULTURE_DIFFICULTIES


def test_culture_catalog_has_no_duplicate_question() -> None:
    normalized_questions = [_normalize(question["question"]) for question in CULTURE_QUESTIONS]
    assert len(normalized_questions) == len(set(normalized_questions))


def test_picker_respects_difficulty_and_excludes_already_asked_questions() -> None:
    easy_questions = {
        question["question"]
        for question in CULTURE_QUESTIONS
        if question["difficulty"] == "facile"
    }
    excluded = set(list(easy_questions)[:-1])

    picked = pick_one_culture_question("facile", excluded)

    assert picked is not None
    assert picked["difficulty"] == "facile"
    assert picked["question"] not in excluded

