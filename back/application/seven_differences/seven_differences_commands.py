from __future__ import annotations

from application.shared.commands import InputModel, Slug


class SevenDifferenceFoundCommand(InputModel):
    difference_id: Slug
