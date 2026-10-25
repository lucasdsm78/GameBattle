from __future__ import annotations

from typing import Self

from domain.shared.models.game_actions import GameActions


class AuctionActions(GameActions):
    """Actions de L’Enchère, portées par la racine d'agrégat de la soirée."""

    __slots__ = ()

    def start_auction(self) -> Self:
        return self._play("auction", lambda game: game.start(self.teams))

    def register_auction_buzzer(self, team: str, now_ms: int) -> Self:
        return self._play("auction", lambda game: game.register_buzzer(self.teams, team))

    def select_auction_bid(self, team: str, target_count: int) -> Self:
        return self._play("auction", lambda game: game.select_bid(self.teams, team, target_count))

    def launch_auction_attempt(self, now_ms: int) -> Self:
        return self._play("auction", lambda game: game.launch(now_ms))

    def change_auction_count(self, delta: int, now_ms: int) -> Self:
        return self._play("auction", lambda game: game.change_count(self.teams, delta, now_ms))

    def expire_auction_attempt(self, now_ms: int) -> Self:
        return self._play("auction", lambda game: game.expire(self.teams, now_ms))

    def next_auction_theme(self) -> Self:
        return self._play("auction", lambda game: game.next_theme())
