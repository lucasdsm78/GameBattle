from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class FlashCalcActions(GameActions):
    __slots__ = ()

    def start_flash_calc(self, now_ms: int) -> Self:
        return self._play("flash_calc", lambda game: game.start(self.teams, now_ms))

    def register_flash_calc_buzzer(self, team: str, now_ms: int) -> Self:
        return self._play("flash_calc", lambda game: game.register_buzzer(self.teams, team, now_ms))

    def pause_flash_calc(self) -> Self:
        return self._play("flash_calc", lambda game: game.pause())

    def resume_flash_calc(self, now_ms: int) -> Self:
        return self._play("flash_calc", lambda game: game.resume(now_ms))
