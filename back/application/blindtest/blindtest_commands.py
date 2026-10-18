from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from application.shared.commands import InputModel

# Positions audio issues des lecteurs natifs : un flottant entier (ex. 12000.0) reste accepté.
DurationMs = Annotated[int, Field(ge=0, le=24 * 60 * 60 * 1000, strict=False)]


class PlaybackControlCommand(InputModel):
    action: Literal["play", "pause", "resume", "stop", "seek"]
    position_ms: DurationMs | None = None


class PlaybackSyncCommand(InputModel):
    track_id: str = Field(default="", max_length=120)
    playback_state: Literal["stopped", "playing", "paused"]
    position_ms: DurationMs = 0
    duration_ms: DurationMs = 0


class PlaylistSeedTrack(InputModel):
    title: str = Field(min_length=1, max_length=120)
    artist: str = Field(min_length=1, max_length=120)
    preview_url: str = Field(default="", max_length=500)
    artwork_url: str = Field(default="", max_length=500)


class PlaylistLoadCommand(InputModel):
    tracks: list[PlaylistSeedTrack] = Field(min_length=1, max_length=100)


class SpotifyPlaylistImportCommand(InputModel):
    playlist_url: str = Field(min_length=10, max_length=500)


class SpotifyTokenCommand(InputModel):
    access_token: str = Field(min_length=1, max_length=2048, pattern=r"^[A-Za-z0-9._~+/=-]+$")
