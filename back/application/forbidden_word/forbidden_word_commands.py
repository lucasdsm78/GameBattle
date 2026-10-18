from __future__ import annotations

from application.shared.commands import InputModel, Slug


class ForbiddenWordCardCommand(InputModel):
    card_id: Slug
