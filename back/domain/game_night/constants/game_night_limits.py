"""Scores, quantités et bornes de la soirée."""

from __future__ import annotations

SUPPORTED_GAME_KEYS = frozenset(
    {
        "blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word",
        "vanishing_word", "flash_calc", "right_flag", "golden_family", "fair_price",
    }
)

DEFAULT_BUZZER_KEYS = ("1", "2", "3", "4", "5", "6")
MAX_TOTAL_ROUNDS = 30
