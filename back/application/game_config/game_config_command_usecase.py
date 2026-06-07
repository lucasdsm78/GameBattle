from __future__ import annotations

from abc import ABC, abstractmethod

from application.game_config.game_config_models import (
    BlindtestAnswerCommandModel,
    BlindtestBuzzerCommandModel,
    BlindtestPlaybackCommandModel,
    BlindtestPlaybackSyncCommandModel,
    BlindtestPlaylistCommandModel,
    GameConfigReadModel,
    GameConfigUpsertModel,
    SpotifyPlaylistImportCommandModel,
)
from domain.game_config.model.game_config import build_blindtest_track
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.spotify.spotify_playlist_service import SpotifyPlaylistService


class GameConfigCommandUseCase(ABC):
    @abstractmethod
    async def replace_config(self, payload: GameConfigUpsertModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def launch_game(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def load_blindtest_playlist(self, payload: BlindtestPlaylistCommandModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def import_blindtest_playlist_from_spotify(
        self, payload: SpotifyPlaylistImportCommandModel
    ) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def register_blindtest_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def answer_blindtest(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def control_blindtest_playback(self, payload: BlindtestPlaybackCommandModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def sync_blindtest_playback(self, payload: BlindtestPlaybackSyncCommandModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def next_blindtest_track(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def set_spotify_user_token(self, access_token: str) -> None:
        raise NotImplementedError


class GameConfigCommandUseCaseImpl(GameConfigCommandUseCase):
    def __init__(self, repository: GameConfigRepository, spotify_playlist_service: SpotifyPlaylistService) -> None:
        self.repository = repository
        self.spotify_playlist_service = spotify_playlist_service

    async def replace_config(self, payload: GameConfigUpsertModel) -> GameConfigReadModel:
        game_config = payload.to_domain().with_timestamp()
        game_config.validate()
        persisted = await self.repository.save(game_config)
        return GameConfigReadModel.from_domain(persisted)

    async def launch_game(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        launched = current.start_session()
        launched.validate()
        persisted = await self.repository.save(launched)
        return GameConfigReadModel.from_domain(persisted)

    async def load_blindtest_playlist(self, payload: BlindtestPlaylistCommandModel) -> GameConfigReadModel:
        current = await self.repository.get_current()
        tracks = [
            build_blindtest_track(
                title=track.title,
                artist=track.artist,
                preview_url=track.preview_url,
                artwork_url=track.artwork_url,
            )
            for track in payload.tracks
        ]
        updated = current.with_blindtest_tracks(tracks, playlist_name="Playlist manuelle", playlist_provider="manual")
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def import_blindtest_playlist_from_spotify(
        self, payload: SpotifyPlaylistImportCommandModel
    ) -> GameConfigReadModel:
        current = await self.repository.get_current()
        spotify_playlist = await self.spotify_playlist_service.import_playlist(payload.playlist_url)
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
        updated = current.with_blindtest_tracks(
            tracks,
            playlist_name=spotify_playlist.playlist_name,
            playlist_source_url=spotify_playlist.playlist_url,
            playlist_provider="spotify",
        )
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def register_blindtest_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.register_buzzer(payload.team.strip())
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def answer_blindtest(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.mark_answer(payload.is_correct)
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def control_blindtest_playback(self, payload: BlindtestPlaybackCommandModel) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.control_playback(payload.action, payload.position_ms)
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def sync_blindtest_playback(self, payload: BlindtestPlaybackSyncCommandModel) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.sync_playback(
            track_id=payload.track_id,
            playback_state=payload.playback_state,
            position_ms=payload.position_ms,
            duration_ms=payload.duration_ms,
        )
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def next_blindtest_track(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.advance_track()
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def set_spotify_user_token(self, access_token: str) -> None:
        self.spotify_playlist_service.set_user_token(access_token)

