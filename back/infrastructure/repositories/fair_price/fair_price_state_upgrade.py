from __future__ import annotations

from dataclasses import asdict
from typing import Any

from domain.fair_price.models.fair_price_state import FairPriceState
from domain.fair_price.services.fair_price_catalog import PRICE_BANDS_BY_ID


def upgrade_fair_price_state(fair_price: dict[str, Any], teams: list[str]) -> dict[str, Any]:
    """Objets retirés du catalogue : la manche en cours est retirée, une manche finie est vidée (vainqueur conservé)."""
    if fair_price.get("phase", "idle") == "idle":
        return fair_price
    band = PRICE_BANDS_BY_ID.get(fair_price.get("band_id", ""))
    known_ids = {item.id for item in band.items} if band else set()
    if set(fair_price.get("item_ids") or ()) <= known_ids and band is not None:
        return fair_price
    if fair_price.get("phase") == "finished":
        return {}
    return asdict(FairPriceState.for_new_manche(teams, round_id=""))
