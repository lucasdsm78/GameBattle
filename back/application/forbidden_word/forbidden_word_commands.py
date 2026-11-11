from __future__ import annotations

from application.shared.commands.fields import Slug
from application.shared.commands.input_model import InputModel


class ForbiddenWordCardCommand(InputModel):
    card_id: Slug
