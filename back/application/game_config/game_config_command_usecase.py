from __future__ import annotations

import logging
import time
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
from domain.game_config.exception.game_config_exception import InvalidGameConfigError
from domain.game_config.model.game_config import GameConfig, build_blindtest_track
from domain.game_config.repository.game_config_repository import GameConfigRepository
from infrastructure.spotify.spotify_playlist_service import SpotifyPlaylistService

logger = logging.getLogger(__name__)


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

    @abstractmethod
    async def reload_default_playlist(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def start_stopchrono(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def stop_stopchrono(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def next_stopchrono_team(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def next_manche(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def reveal_next_ranking(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def start_culture(self) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def register_culture_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def answer_culture(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        raise NotImplementedError

    @abstractmethod
    async def next_culture_question(self) -> GameConfigReadModel:
        raise NotImplementedError


class GameConfigCommandUseCaseImpl(GameConfigCommandUseCase):
    def __init__(
        self,
        repository: GameConfigRepository,
        spotify_playlist_service: SpotifyPlaylistService,
        default_playlist_url: str = "",
    ) -> None:
        self.repository = repository
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

    async def _autoimport_blindtest(self, config: GameConfig) -> GameConfig:
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

    async def replace_config(self, payload: GameConfigUpsertModel) -> GameConfigReadModel:
        game_config = payload.to_domain().with_timestamp()
        game_config.validate()
        persisted = await self.repository.save(game_config)
        return GameConfigReadModel.from_domain(persisted)

    async def launch_game(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        launched = await self._autoimport_blindtest(current.start_session())
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
        updated = await self._apply_spotify_playlist(current, payload.playlist_url)
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def reload_default_playlist(self) -> GameConfigReadModel:
        if not self._default_playlist_url:
            raise InvalidGameConfigError(
                "Aucune playlist blindtest n'est configurée côté serveur (GAMEBATTLE_BLINDTEST_PLAYLIST_URL)."
            )
        current = await self.repository.get_current()
        updated = await self._apply_spotify_playlist(current, self._default_playlist_url)
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

    async def start_stopchrono(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.start_chrono(int(time.time() * 1000))
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def stop_stopchrono(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.stop_chrono(int(time.time() * 1000))
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def next_stopchrono_team(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.next_chrono_team()
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def next_manche(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        advanced = await self._autoimport_blindtest(current.next_manche())
        advanced.validate()
        persisted = await self.repository.save(advanced)
        return GameConfigReadModel.from_domain(persisted)

    async def reveal_next_ranking(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.reveal_next_ranking()
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def start_culture(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.start_culture()
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def register_culture_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.register_culture_buzzer(payload.team.strip())
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def answer_culture(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.answer_culture(payload.is_correct)
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

    async def next_culture_question(self) -> GameConfigReadModel:
        current = await self.repository.get_current()
        updated = current.next_culture_question()
        updated.validate()
        persisted = await self.repository.save(updated)
        return GameConfigReadModel.from_domain(persisted)

