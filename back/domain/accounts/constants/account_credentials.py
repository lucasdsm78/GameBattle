"""Bornes des pseudos et des mots de passe."""

from __future__ import annotations

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128  # au-delà, rien de plus sûr, seulement un hachage plus coûteux
PSEUDO_MIN_LENGTH = 3
PSEUDO_MAX_LENGTH = 20
