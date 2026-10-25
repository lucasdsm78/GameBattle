from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class CultureActions(GameActions):
    """Actions de Culture générale, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_culture(self) -> Self:
        return self._play("culture", lambda game: game.start())

    def select_culture_difficulty(self, difficulty: str) -> Self:
        round_id = self.session.active_round.round_id if self.session.active_round else ""
        return self._play("culture", lambda game: game.select_difficulty(difficulty, round_id))

    def register_culture_buzzer(self, team: str) -> Self:
        return self._play("culture", lambda game: game.register_buzzer(team))

    def answer_culture(self, is_correct: bool) -> Self:
        return self._play("culture", lambda game: game.answer(is_correct))

    def next_culture_question(self) -> Self:
        return self._play("culture", lambda game: game.next_question())
