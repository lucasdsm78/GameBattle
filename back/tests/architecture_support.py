from __future__ import annotations

from support import BACK_DIR

GAME_MODULES = (
    "blindtest", "culture", "stopchrono", "bombe", "memory", "seven_differences", "auction", "forbidden_word", "vanishing_word",
    "flash_calc", "right_flag", "golden_family", "fair_price",
)


DATABASE_DIR = BACK_DIR / "infrastructure" / "database"


DATABASE_MODULE_DIRS = {"accounts": "accounts", "game_sessions": "game_night"}  # dossier -> module du domaine


REPOSITORIES_DIR = BACK_DIR / "infrastructure" / "repositories"
