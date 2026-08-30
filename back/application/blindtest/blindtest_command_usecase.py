from __future__ import annotations

import logging

from application.blindtest.spotify_playlist_port import SpotifyPlaylistProvider
from application.game_config.command.base import GameConfigCommandBase
from application.game_config.game_config_models import (
    BlindtestAnswerCommandModel,
    BlindtestBuzzerCommandModel,
    BlindtestPlaybackCommandModel,
    BlindtestPlaybackSyncCommandModel,
    BlindtestPlaylistCommandModel,
    GameConfigReadModel,
    SpotifyPlaylistImportCommandModel,
)
from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import GameConfig, build_blindtest_track
from domain.game_config.repository.game_config_repository import GameConfigRepository

logger = logging.getLogger(__name__)


class BlindtestCommandUseCase(GameConfigCommandBase):

    def __init__(
        self,
        repository: GameConfigRepository,
        spotify_playlist_service: SpotifyPlaylistProvider,
        default_playlist_url: str = "",
    ) -> None:
        super().__init__(repository)
        self.spotify_playlist_service = spotify_playlist_service
        self._default_playlist_url = (default_playlist_url or "").strip()

    async def _apply_spotify_playlist(self, config: GameConfig, playlist_url: str) -> GameConfig:
        spotify_playlist = await self.spotify_playlist_service.import_playlist(playlist_url)
        tracks = [
            build_blindtest_track(
                track_id=track.track_id,
                title=track.title,
                artist=track.artist,
                preview_url=track.preview_url,
                artwork_url=track.artwork_url,
            )
            for track in spotify_playlist.tracks
        ]
        return config.with_blindtest_tracks(
            tracks,
            playlist_name=spotify_playlist.playlist_name,
            playlist_source_url=spotify_playlist.playlist_url,
            playlist_provider="spotify",
        )

    async def autoimport(self, config: GameConfig) -> GameConfig:
        """Importe la playlist fixe (best-effort) quand on entre dans une manche blindtest sans pistes."""
        active_round = config.session.active_round
        if (
            active_round is not None
            and active_round.game_key == "blindtest"
            and not config.session.blindtest.tracks
            and self._default_playlist_url
            and self.spotify_playlist_service.has_user_token
        ):
            try:
                return await self._apply_spotify_playlist(config, self._default_playlist_url)
            except InvalidGameConfigError as exc:
                logger.warning("blindtest.autoimport.failed", extra={"detail": exc.message})
        return config

    async def load_playlist(self, payload: BlindtestPlaylistCommandModel) -> GameConfigReadModel:
        tracks = [
            build_blindtest_track(
                title=track.title,
                artist=track.artist,
                preview_url=track.preview_url,
                artwork_url=track.artwork_url,
            )
            for track in payload.tracks
        ]
        return await self._mutate(
            lambda config: config.with_blindtest_tracks(
                tracks, playlist_name="Playlist manuelle", playlist_provider="manual"
            )
        )

    async def import_playlist_from_spotify(
        self, payload: SpotifyPlaylistImportCommandModel
    ) -> GameConfigReadModel:
        return await self._mutate(lambda config: self._apply_spotify_playlist(config, payload.playlist_url))

    async def reload_default_playlist(self) -> GameConfigReadModel:
        if not self._default_playlist_url:
            raise InvalidGameConfigError(
                "Aucune playlist blindtest n'est configurée côté serveur (GAMEBATTLE_BLINDTEST_PLAYLIST_URL)."
            )
        return await self._mutate(lambda config: self._apply_spotify_playlist(config, self._default_playlist_url))

    async def register_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.register_buzzer(payload.team.strip()))

    async def answer(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.mark_answer(payload.is_correct))

    async def control_playback(self, payload: BlindtestPlaybackCommandModel) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.control_playback(payload.action, payload.position_ms))

    async def sync_playback(self, payload: BlindtestPlaybackSyncCommandModel) -> GameConfigReadModel:
        return await self._mutate(
            lambda config: config.sync_playback(
                track_id=payload.track_id,
                playback_state=payload.playback_state,
                position_ms=payload.position_ms,
                duration_ms=payload.duration_ms,
            )
        )

    async def next_track(self) -> GameConfigReadModel:
        return await self._mutate(lambda config: config.advance_track())

    async def set_spotify_user_token(self, access_token: str) -> None:
        self.spotify_playlist_service.set_user_token(access_token)
