from __future__ import annotations

from abc import ABC, abstractmethod

from application.blindtest.spotify_playlist_port import SpotifyPlaylistProvider
from application.blindtest.blindtest_command_usecase import BlindtestCommandUseCase
from application.culture.culture_command_usecase import CultureCommandUseCase
from application.session.session_command_usecase import SessionCommandUseCase
from application.stopchrono.stopchrono_command_usecase import StopchronoCommandUseCase
from application.game_config.game_config_models import (
    BlindtestAnswerCommandModel,
    BlindtestBuzzerCommandModel,
    BlindtestPlaybackCommandModel,
    BlindtestPlaybackSyncCommandModel,
    BlindtestPlaylistCommandModel,
    CultureDifficultyCommandModel,
    GameConfigReadModel,
    GameConfigUpsertModel,
    SpotifyPlaylistImportCommandModel,
)
from domain.game_config.repository.game_config_repository import GameConfigRepository


class GameConfigCommandUseCase(ABC):
    @abstractmethod
    async def replace_config(self, payload: GameConfigUpsertModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def launch_game(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def load_blindtest_playlist(self, payload: BlindtestPlaylistCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def import_blindtest_playlist_from_spotify(
        self, payload: SpotifyPlaylistImportCommandModel
    ) -> GameConfigReadModel: ...

    @abstractmethod
    async def register_blindtest_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def answer_blindtest(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def control_blindtest_playback(self, payload: BlindtestPlaybackCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def sync_blindtest_playback(self, payload: BlindtestPlaybackSyncCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def next_blindtest_track(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def set_spotify_user_token(self, access_token: str) -> None: ...

    @abstractmethod
    async def reload_default_playlist(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def start_stopchrono(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def stop_stopchrono(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def next_stopchrono_team(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def next_manche(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def reveal_next_ranking(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def start_culture(self) -> GameConfigReadModel: ...

    @abstractmethod
    async def select_culture_difficulty(self, payload: CultureDifficultyCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def register_culture_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def answer_culture(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel: ...

    @abstractmethod
    async def next_culture_question(self) -> GameConfigReadModel: ...


class GameConfigCommandUseCaseImpl(GameConfigCommandUseCase):
    """Façade qui expose le contrat unifié en déléguant à un use case par jeu.

    Tous les sous-use-cases partagent le même agrégat GameConfig via le dépôt injecté.
    """

    def __init__(
        self,
        repository: GameConfigRepository,
        spotify_playlist_service: SpotifyPlaylistProvider,
        default_playlist_url: str = "",
    ) -> None:
        self._blindtest = BlindtestCommandUseCase(repository, spotify_playlist_service, default_playlist_url)
        self._culture = CultureCommandUseCase(repository)
        self._stopchrono = StopchronoCommandUseCase(repository)
        self._session = SessionCommandUseCase(repository, self._blindtest)

    # --- Session ---
    async def replace_config(self, payload: GameConfigUpsertModel) -> GameConfigReadModel:
        return await self._session.replace_config(payload)

    async def launch_game(self) -> GameConfigReadModel:
        return await self._session.launch_game()

    async def next_manche(self) -> GameConfigReadModel:
        return await self._session.next_manche()

    async def reveal_next_ranking(self) -> GameConfigReadModel:
        return await self._session.reveal_next_ranking()

    # --- Blindtest ---
    async def load_blindtest_playlist(self, payload: BlindtestPlaylistCommandModel) -> GameConfigReadModel:
        return await self._blindtest.load_playlist(payload)

    async def import_blindtest_playlist_from_spotify(
        self, payload: SpotifyPlaylistImportCommandModel
    ) -> GameConfigReadModel:
        return await self._blindtest.import_playlist_from_spotify(payload)

    async def reload_default_playlist(self) -> GameConfigReadModel:
        return await self._blindtest.reload_default_playlist()

    async def register_blindtest_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        return await self._blindtest.register_buzzer(payload)

    async def answer_blindtest(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        return await self._blindtest.answer(payload)

    async def control_blindtest_playback(self, payload: BlindtestPlaybackCommandModel) -> GameConfigReadModel:
        return await self._blindtest.control_playback(payload)

    async def sync_blindtest_playback(self, payload: BlindtestPlaybackSyncCommandModel) -> GameConfigReadModel:
        return await self._blindtest.sync_playback(payload)

    async def next_blindtest_track(self) -> GameConfigReadModel:
        return await self._blindtest.next_track()

    async def set_spotify_user_token(self, access_token: str) -> None:
        await self._blindtest.set_spotify_user_token(access_token)

    # --- Stopchrono ---
    async def start_stopchrono(self) -> GameConfigReadModel:
        return await self._stopchrono.start()

    async def stop_stopchrono(self) -> GameConfigReadModel:
        return await self._stopchrono.stop()

    async def next_stopchrono_team(self) -> GameConfigReadModel:
        return await self._stopchrono.next_team()

    # --- Culture ---
    async def start_culture(self) -> GameConfigReadModel:
        return await self._culture.start()

    async def select_culture_difficulty(self, payload: CultureDifficultyCommandModel) -> GameConfigReadModel:
        return await self._culture.select_difficulty(payload)

    async def register_culture_buzzer(self, payload: BlindtestBuzzerCommandModel) -> GameConfigReadModel:
        return await self._culture.register_buzzer(payload)

    async def answer_culture(self, payload: BlindtestAnswerCommandModel) -> GameConfigReadModel:
        return await self._culture.answer(payload)

    async def next_culture_question(self) -> GameConfigReadModel:
        return await self._culture.next_question()
