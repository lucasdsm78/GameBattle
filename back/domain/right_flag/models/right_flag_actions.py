from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class RightFlagActions(GameActions):
    __slots__ = ()

    def start_right_flag(self, now_ms: int) -> Self:
        return self._play("right_flag", lambda game: game.start(self.teams, now_ms))

    def register_right_flag_buzzer(self, team: str, now_ms: int) -> Self:
        return self._play("right_flag", lambda game: game.register_buzzer(self.teams, team, now_ms))

    def pause_right_flag(self) -> Self:
        return self._play("right_flag", lambda game: game.pause())

    def resume_right_flag(self, now_ms: int) -> Self:
        return self._play("right_flag", lambda game: game.resume(now_ms))
