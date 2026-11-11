from __future__ import annotations

from pydantic import Field

from application.shared.commands.input_model import InputModel


class SpotifyPlaylistImportCommand(InputModel):
    playlist_url: str = Field(min_length=10, max_length=500)
