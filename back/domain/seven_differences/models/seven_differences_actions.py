from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class SevenDifferencesActions(GameActions):
    """Actions des 7 différences, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_seven_differences(self, now_ms: int) -> Self:
        return self._play("seven_differences", lambda game: game.start(self.teams, now_ms))

    def open_seven_differences(self, now_ms: int) -> Self:
        return self._play("seven_differences", lambda game: game.open(now_ms))

    def register_seven_differences_buzzer(self, team: str, now_ms: int) -> Self:
        return self._play("seven_differences", lambda game: game.register_buzzer(self.teams, team, now_ms))

    def find_seven_difference(self, difference_id: str) -> Self:
        return self._play("seven_differences", lambda game: game.find(self.teams, difference_id))

    def reject_seven_differences_answer(self) -> Self:
        return self._play("seven_differences", lambda game: game.reject())
