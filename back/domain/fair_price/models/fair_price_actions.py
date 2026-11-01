from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class FairPriceActions(GameActions):
    __slots__ = ()

    def start_fair_price_turn(self, now_ms: int) -> Self:
        return self._play("fair_price", lambda game: game.start_turn(now_ms))

    def give_fair_price_hint(self, direction: str, proposals: int, now_ms: int) -> Self:
        return self._play("fair_price", lambda game: game.give_hint(direction, proposals, now_ms))

    def mark_fair_price_found(self, proposals: int, now_ms: int) -> Self:
        return self._play("fair_price", lambda game: game.mark_found(proposals, now_ms))
