from __future__ import annotations

from typing import Optional, Self

from domain.blindtest.models.blindtest_track import BlindtestTrack
from domain.shared.models.game_actions import GameActions


class BlindtestActions(GameActions):
    """Actions du Blindtest, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def with_blindtest_tracks(
        self,
        tracks: list[BlindtestTrack],
        playlist_name: str = "",
        playlist_source_url: str = "",
        playlist_provider: str = "manual",
    ) -> Self:
        return self._play(
            "blindtest",
            lambda game: game.with_tracks(
                tracks, playlist_name=playlist_name, playlist_source_url=playlist_source_url, playlist_provider=playlist_provider
            ),
        )

    def register_buzzer(self, team: str) -> Self:
        return self._play("blindtest", lambda game: game.register_buzzer(team))

    def mark_answer(self, is_correct: bool) -> Self:
        return self._play("blindtest", lambda game: game.mark_answer(is_correct))

    def control_playback(self, action: str, position_ms: Optional[int] = None) -> Self:
        return self._play("blindtest", lambda game: game.control_playback(action, position_ms))

    def sync_playback(self, track_id: str, playback_state: str, position_ms: int, duration_ms: int = 0) -> Self:
        return self._play("blindtest", lambda game: game.sync_playback(track_id, playback_state, position_ms, duration_ms))

    def advance_track(self) -> Self:
        return self._play("blindtest", lambda game: game.advance_track())
