from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from exceptions import InvalidGameConfigError


@dataclass(slots=True)
class BlindtestTrack:
    track_id: str
    title: str
    artist: str
    preview_url: str = ""
    artwork_url: str = ""

    def validate(self) -> None:
        if len(self.track_id.strip()) < 2:
            raise InvalidGameConfigError("Chaque musique doit avoir un identifiant Spotify valide.")
        if len(self.title.strip()) < 1 or len(self.artist.strip()) < 1:
            raise InvalidGameConfigError("Chaque musique doit avoir un titre et un artiste.")
        if self.preview_url.strip() and len(self.preview_url.strip()) < 8:
            raise InvalidGameConfigError("L'URL de lecture d'une musique est invalide.")


def build_blindtest_track(
    title: str,
    artist: str,
    preview_url: str,
    artwork_url: str = "",
    track_id: Optional[str] = None,
) -> BlindtestTrack:
    return BlindtestTrack(
        track_id=track_id or f"track-{uuid4().hex[:12]}",
        title=title,
        artist=artist,
        preview_url=preview_url,
        artwork_url=artwork_url,
    )
