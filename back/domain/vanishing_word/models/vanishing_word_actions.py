from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class VanishingWordActions(GameActions):
    """Actions du Mot qui disparaît, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_vanishing_round(self, now_ms: int) -> Self:
        return self._play("vanishing_word", lambda game: game.start_round(self.teams, now_ms))

    def register_vanishing_buzzer(self, team: str, now_ms: int) -> Self:
        return self._play("vanishing_word", lambda game: game.register_buzzer(self.teams, team, now_ms))

    def judge_vanishing_word(self, found: bool) -> Self:
        return self._play("vanishing_word", lambda game: game.judge(self.teams, found))

    def reveal_vanishing_word(self) -> Self:
        return self._play("vanishing_word", lambda game: game.reveal())
