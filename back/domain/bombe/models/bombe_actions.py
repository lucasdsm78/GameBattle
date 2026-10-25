from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class BombeActions(GameActions):
    """Actions de La Bombe, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_bombe(self, now_ms: int) -> Self:
        started = self._play("bombe", lambda game: game.start(self.teams, self.session.last_bombe_roller_index))
        return started._replace_session(last_bombe_roller_index=started.session.bombe.roller_team_index)

    def register_bombe_buzzer(self, team: str, now_ms: int) -> Self:
        return self._play("bombe", lambda game: game.register_buzzer(self.teams, team, now_ms))

    def begin_bombe_after_roll(self, now_ms: int) -> Self:
        return self._play("bombe", lambda game: game.begin_after_roll(now_ms))

    def previous_bombe_team(self, now_ms: int) -> Self:
        return self._play("bombe", lambda game: game.previous_team(self.teams, now_ms))

    def explode_bombe(self, now_ms: int) -> Self:
        return self._play("bombe", lambda game: game.explode(self.teams, now_ms))
