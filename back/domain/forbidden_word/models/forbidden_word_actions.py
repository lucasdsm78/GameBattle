from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class ForbiddenWordActions(GameActions):
    """Actions du Mot interdit, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_forbidden_word_turn(self, now_ms: int) -> Self:
        return self._play("forbidden_word", lambda game: game.start_turn(now_ms))

    def resolve_forbidden_word_card(self, card_id: str, *, found: bool, now_ms: int) -> Self:
        return self._play("forbidden_word", lambda game: game.resolve_card(self.teams, card_id, found=found, now_ms=now_ms))
