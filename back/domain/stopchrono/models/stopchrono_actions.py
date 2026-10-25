from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class StopChronoActions(GameActions):
    """Actions du Stop Chrono, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_chrono(self, now_ms: int) -> Self:
        return self._play("stopchrono", lambda game: game.start(now_ms))

    def stop_chrono(self, now_ms: int) -> Self:
        return self._play("stopchrono", lambda game: game.stop(self.teams, now_ms))

    def next_chrono_team(self) -> Self:
        return self._play("stopchrono", lambda game: game.next_team(self.teams))
