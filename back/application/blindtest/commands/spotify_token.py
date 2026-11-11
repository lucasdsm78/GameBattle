from __future__ import annotations

from pydantic import Field

from application.shared.commands.input_model import InputModel


class SpotifyTokenCommand(InputModel):
    access_token: str = Field(min_length=1, max_length=2048, pattern=r"^[A-Za-z0-9._~+/=-]+$")
