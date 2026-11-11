from __future__ import annotations

from pydantic import Field

from application.blindtest.commands.playlist_seed_track import PlaylistSeedTrack
from application.shared.commands.input_model import InputModel


class PlaylistLoadCommand(InputModel):
    tracks: list[PlaylistSeedTrack] = Field(min_length=1, max_length=100)
