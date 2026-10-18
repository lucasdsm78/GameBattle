from __future__ import annotations

from application.blindtest.blindtest_commands import (
    PlaybackControlCommand,
    PlaybackSyncCommand,
    PlaylistLoadCommand,
    SpotifyPlaylistImportCommand,
    SpotifyTokenCommand,
)
from application.shared.command_usecase import CommandUseCase
from application.shared.commands import AnswerCommand, TeamCommand
from application.shared.snapshot import GameConfigSnapshot
from domain.vo.blindtest_track import build_blindtest_track


class BlindtestCommandUseCase(CommandUseCase):
    async def load_playlist(self, command: PlaylistLoadCommand) -> GameConfigSnapshot | None:
        tracks = [
            build_blindtest_track(title=track.title, artist=track.artist, preview_url=track.preview_url, artwork_url=track.artwork_url)
            for track in command.tracks
        ]
        return await self._execute(
            lambda config, ctx: config.with_blindtest_tracks(tracks, playlist_name="Playlist manuelle", playlist_provider="manual")
        )

    async def import_spotify_playlist(self, command: SpotifyPlaylistImportCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: ctx.playlists.import_playlist(config, command.playlist_url))

    async def reload_default_playlist(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: ctx.playlists.reload_default(config))

    async def register_buzzer(self, command: TeamCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.register_buzzer(command.team))

    async def answer(self, command: AnswerCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.mark_answer(command.is_correct))

    async def control_playback(self, command: PlaybackControlCommand) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.control_playback(command.action, command.position_ms))

    async def sync_playback(self, command: PlaybackSyncCommand) -> GameConfigSnapshot | None:
        return await self._execute(
            lambda config, ctx: config.sync_playback(command.track_id, command.playback_state, command.position_ms, command.duration_ms)
        )

    async def next_track(self) -> GameConfigSnapshot | None:
        return await self._execute(lambda config, ctx: config.advance_track())

    async def set_spotify_user_token(self, command: SpotifyTokenCommand) -> None:
        # Aucun état de partie modifié : pas de verrou, pas de diffusion.
        self._playlists.set_user_token(command.access_token)
