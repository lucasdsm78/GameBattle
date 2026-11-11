from __future__ import annotations

from typing import Literal

from application.fair_price.commands.fair_price_found import FairPriceFoundCommand


class FairPriceHintCommand(FairPriceFoundCommand):
    direction: Literal["plus", "moins"]
