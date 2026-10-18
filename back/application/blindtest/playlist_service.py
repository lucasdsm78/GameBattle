from __future__ import annotations

import logging

from application.blindtest.spotify_playlist_port import SpotifyPlaylistProvider
from domain.models.game_config import GameConfig
from domain.vo.blindtest_track import build_blindtest_track
from exceptions import InvalidGameConfigError

logger = logging.getLogger(__name__)


class BlindtestPlaylistService:
    def __init__(self, provider: SpotifyPlaylistProvider, default_playlist_url: str = "") -> None:
        self._provider = provider
        self._default_playlist_url = default_playlist_url.strip()

    def set_user_token(self, token: str) -> None:
        self._provider.set_user_token(token)

    async def import_playlist(self, config: GameConfig, playlist_url: str) -> GameConfig:
        playlist = await self._provider.import_playlist(playlist_url)
        tracks = [
            build_blindtest_track(
                track_id=track.track_id,
                title=track.title,
                artist=track.artist,
                preview_url=track.preview_url,
                artwork_url=track.artwork_url,
            )
            for track in playlist.tracks
        ]
        return config.with_blindtest_tracks(
            tracks,
            playlist_name=playlist.playlist_name,
            playlist_source_url=playlist.playlist_url,
            playlist_provider="spotify",
        )

    async def reload_default(self, config: GameConfig) -> GameConfig:
        if not self._default_playlist_url:
            raise InvalidGameConfigError(
                "Aucune playlist blindtest n'est configurée côté serveur (GAMEBATTLE_BLINDTEST_PLAYLIST_URL)."
            )
        return await self.import_playlist(config, self._default_playlist_url)

    async def autoimport(self, config: GameConfig) -> GameConfig:
        """Importe la playlist par défaut (au mieux) en entrant dans une manche blindtest sans musiques."""
        active_round = config.session.active_round
        if (
            active_round is None
            or active_round.game_key != "blindtest"
            or config.session.blindtest.tracks
            or not self._default_playlist_url
            or not self._provider.has_user_token
        ):
            return config
        try:
            return await self.import_playlist(config, self._default_playlist_url)
        except InvalidGameConfigError as exc:
            logger.warning("blindtest.autoimport.failed", extra={"detail": exc.message})
            return config
