from __future__ import annotations

from typing import Protocol


class SpotifyPlaylistTrack(Protocol):
    track_id: str
    title: str
    artist: str
    preview_url: str
    artwork_url: str


class SpotifyPlaylistImport(Protocol):
    playlist_id: str
    playlist_name: str
    playlist_url: str
    tracks: list[SpotifyPlaylistTrack]


class SpotifyPlaylistProvider(Protocol):
    @property
    def has_user_token(self) -> bool: ...

    async def import_playlist(self, playlist_reference: str) -> SpotifyPlaylistImport: ...

    def set_user_token(self, token: str) -> None: ...

