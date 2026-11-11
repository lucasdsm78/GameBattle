from __future__ import annotations

from dataclasses import asdict
from typing import Any

from application.fair_price.fair_price_rules import FAIR_PRICE_RULES
from application.shared.game_presenter import GamePresenter
from domain.fair_price.constants.fair_price_timing import FAIR_PRICE_TURN_MS
from domain.fair_price.models.fair_price_state import FairPriceState
from domain.fair_price.services.fair_price_catalog import (
    PRICE_BANDS_BY_ID,
    PRICE_ITEMS_BY_ID,
    PRICES_CHECKED_ON,
)


class FairPricePresenter(GamePresenter[FairPriceState]):
    rules = FAIR_PRICE_RULES

    # Les objets des équipes qui n'ont pas encore joué ne quittent pas le serveur.
    internal_fields = frozenset({"item_ids"})

    def extras(self, state: FairPriceState, teams: list[str]) -> dict[str, Any]:
        band = PRICE_BANDS_BY_ID.get(state.band_id)
        item = state.current_item
        return {
            "turn_ms": FAIR_PRICE_TURN_MS,
            "band_label": band.label if band else "",
            "prices_checked_on": PRICES_CHECKED_ON,
            "current_team": state.current_team,
            "current_item": asdict(item) if item else None,
            # Le prix d'un objet n'est public qu'une fois son tour terminé.
            "results": [{**asdict(result), "item": asdict(PRICE_ITEMS_BY_ID[result.item_id])} for result in state.results],
        }

    def display_view(self, controller_view: dict[str, Any]) -> dict[str, Any]:
        # L'écran ne montre l'objet qu'une fois le chrono lancé, et jamais son prix avant la fin du tour.
        item = controller_view.get("current_item")
        if not item:
            return controller_view
        shown = {**item, "price": None} if controller_view.get("phase") == "running" else None
        return {**controller_view, "current_item": shown}
