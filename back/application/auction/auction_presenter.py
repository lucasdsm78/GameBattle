from __future__ import annotations

from typing import Any

from application.shared.game_presenter import GamePresenter
from domain.auction.models.auction_state import AuctionState


class AuctionPresenter(GamePresenter[AuctionState]):
    internal_fields = frozenset({"asked_theme_ids"})

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        return {**controller_view, "answers": []}
