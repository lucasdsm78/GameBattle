from __future__ import annotations

from support import BACK_DIR

GAME_MODULES = (
    "blindtest", "culture", "stopchrono", "bombe", "memory", "seven_differences", "auction", "forbidden_word", "vanishing_word",
    "flash_calc", "right_flag", "golden_family", "fair_price",
)


DATABASE_DIR = BACK_DIR / "infrastructure" / "database"


# Dossier -> module : un dossier par bounded context ; `rate_limiting` relève du noyau partagé (comptes et salons).
DATABASE_MODULE_DIRS = {
    "accounts": "accounts",
    "game_sessions": "game_night",
    "rooms": "rooms",
    "rate_limiting": "shared",
    "outbox": "shared",
}


REPOSITORIES_DIR = BACK_DIR / "infrastructure" / "repositories"
