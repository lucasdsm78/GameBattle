from __future__ import annotations

from dataclasses import asdict
from typing import Any

from domain.fair_price.models.fair_price_state import FairPriceState
from domain.fair_price.services.fair_price_catalog import PRICE_BANDS_BY_ID
from infrastructure.database.games.shared.game_state_mapper import GameStateMapper


class FairPriceMapper(GameStateMapper[FairPriceState]):
    state_type = FairPriceState
    schema_version = 1

    def repair(self, document: dict[str, Any], teams: list[str]) -> dict[str, Any]:
        """Objets retirés du catalogue : la manche en cours est retirée, une manche finie est vidée (vainqueur conservé)."""
        if document.get("phase", "idle") == "idle":
            return document
        band = PRICE_BANDS_BY_ID.get(document.get("band_id", ""))
        known_ids = {item.id for item in band.items} if band else set()
        if set(document.get("item_ids") or ()) <= known_ids and band is not None:
            return document
        if document.get("phase") == "finished":
            return {}
        return asdict(FairPriceState.for_new_manche(teams, round_id=""))
