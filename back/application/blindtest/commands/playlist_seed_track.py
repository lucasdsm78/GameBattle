from __future__ import annotations

from pydantic import Field

from application.shared.commands.input_model import InputModel


class PlaylistSeedTrack(InputModel):
    title: str = Field(min_length=1, max_length=120)
    artist: str = Field(min_length=1, max_length=120)
    preview_url: str = Field(default="", max_length=500)
    artwork_url: str = Field(default="", max_length=500)
