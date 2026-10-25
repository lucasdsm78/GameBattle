from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class GoldenFamilyActions(GameActions):
    __slots__ = ()

    def show_next_family_question(self) -> Self:
        return self._play("golden_family", lambda game: game.show_next_question(self.teams))

    def register_golden_family_buzzer(self, team: str, now_ms: int) -> Self:
        return self._play("golden_family", lambda game: game.register_buzzer(self.teams, team))

    def give_family_answer(self, answer_index: int, turn: int) -> Self:
        return self._play("golden_family", lambda game: game.give_answer(self.teams, answer_index, turn))

    def strike_family_answer(self, turn: int) -> Self:
        return self._play("golden_family", lambda game: game.strike(self.teams, turn))

    def reveal_family_board(self) -> Self:
        return self._play("golden_family", lambda game: game.reveal_all())
