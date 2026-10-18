from __future__ import annotations

from application.game_config.command_bus import CONTROLLER_AND_DISPLAY, CommandContext, CommandSpec
from application.game_config.game_config_models import (
    AnswerCommand,
    PlaybackControlCommand,
    PlaybackSyncCommand,
    PlaylistLoadCommand,
    SpotifyPlaylistImportCommand,
    SpotifyTokenCommand,
    TeamCommand,
)
from domain.game_config.model.game_config import GameConfig
from domain.game_config.model.games.blindtest import build_blindtest_track


def _load_manual_playlist(config: GameConfig, command: PlaylistLoadCommand, context: CommandContext) -> GameConfig:
    tracks = [
        build_blindtest_track(title=track.title, artist=track.artist, preview_url=track.preview_url, artwork_url=track.artwork_url)
        for track in command.tracks
    ]
    return config.with_blindtest_tracks(tracks, playlist_name="Playlist manuelle", playlist_provider="manual")


def _store_spotify_token(config: GameConfig, command: SpotifyTokenCommand, context: CommandContext) -> GameConfig:
    context.playlists.set_user_token(command.access_token)
    return config


BLINDTEST_COMMANDS = (
    CommandSpec("blindtest.playlist.load", _load_manual_playlist, PlaylistLoadCommand),
    CommandSpec(
        "blindtest.playlist.import-spotify",
        lambda config, command, context: context.playlists.import_playlist(config, command.playlist_url),
        SpotifyPlaylistImportCommand,
    ),
    CommandSpec("blindtest.playlist.reload", lambda config, _, context: context.playlists.reload_default(config)),
    CommandSpec(
        "blindtest.buzzer", lambda config, command, _: config.register_buzzer(command.team), TeamCommand, CONTROLLER_AND_DISPLAY
    ),
    CommandSpec("blindtest.answer", lambda config, command, _: config.mark_answer(command.is_correct), AnswerCommand),
    CommandSpec(
        "blindtest.playback.control",
        lambda config, command, _: config.control_playback(command.action, command.position_ms),
        PlaybackControlCommand,
    ),
    CommandSpec(
        "blindtest.playback.sync",
        lambda config, command, _: config.sync_playback(
            command.track_id, command.playback_state, command.position_ms, command.duration_ms
        ),
        PlaybackSyncCommand,
    ),
    CommandSpec("blindtest.next-track", lambda config, *_: config.advance_track()),
    CommandSpec("spotify.user-token", _store_spotify_token, SpotifyTokenCommand, CONTROLLER_AND_DISPLAY),
)
