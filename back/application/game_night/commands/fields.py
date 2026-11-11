from __future__ import annotations

from typing import Literal

GameKey = Literal[
    "blindtest", "stopchrono", "culture", "bombe", "memory", "seven_differences", "auction", "forbidden_word",
    "vanishing_word", "flash_calc", "right_flag", "golden_family", "fair_price",
]
GameStatus = Literal["configuring", "ready", "live", "finished"]
