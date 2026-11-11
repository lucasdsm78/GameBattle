from __future__ import annotations

import hashlib
from typing import Optional, TypeGuard

SESSION_TOKEN_BYTES = 32
MAX_SESSION_TOKEN_LENGTH = 128


def hash_session_token(token: str) -> str:
    # Le jeton est aléatoire (256 bits) : un SHA-256 suffit, pas besoin d'un hachage lent comme pour un mot de passe.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_plausible_token(token: Optional[str]) -> TypeGuard[str]:
    """Un jeton absent ou démesuré n'est même pas cherché en base."""
    return bool(token) and len(token) <= MAX_SESSION_TOKEN_LENGTH
