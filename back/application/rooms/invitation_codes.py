from __future__ import annotations

import secrets

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O ni 1/I : lisible à voix haute
CODE_LENGTH = 10  # 32^10 ≈ 10^15 codes : introuvable par essais, d'autant que les essais sont limités
INVITATION_MISSING = "Ce lien d'invitation n'existe pas ou a expiré."


def new_invitation_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
