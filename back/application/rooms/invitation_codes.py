from __future__ import annotations

import secrets

from application.rooms.constants.invitations import CODE_ALPHABET, CODE_LENGTH


def new_invitation_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
