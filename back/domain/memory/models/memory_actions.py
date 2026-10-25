from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class MemoryActions(GameActions):
    """Actions de Mémoire en chaîne, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_memory(self) -> Self:
        return self._play("memory", lambda game: game.start(self.teams))

    def next_memory_question(self) -> Self:
        return self._play("memory", lambda game: game.next_question())

    def validate_memory_sequence(self) -> Self:
        return self._play("memory", lambda game: game.validate_sequence())

    def disqualify_memory_team(self) -> Self:
        return self._play("memory", lambda game: game.disqualify_team(self.teams))
