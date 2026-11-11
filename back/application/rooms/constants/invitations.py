"""Liens d'invitation : format du code (secret), chemin du lien, message quand il n'existe plus."""

from __future__ import annotations

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O ni 1/I : lisible à voix haute
CODE_LENGTH = 10  # 32^10 ≈ 10^15 codes : introuvable par essais, d'autant que les essais sont limités
INVITATION_MISSING = "Ce lien d'invitation n'existe pas ou a expiré."
INVITE_PATH = "/join/{code}"
