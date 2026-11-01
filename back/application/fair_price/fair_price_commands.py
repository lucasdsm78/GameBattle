from __future__ import annotations

from typing import Literal

from pydantic import Field

from application.shared.commands import InputModel


class FairPriceFoundCommand(InputModel):
    # Réponses déjà jugées vues par la régie : un double appui ou un message rejoué est ignoré.
    proposals: int = Field(ge=0, le=10_000)


class FairPriceHintCommand(FairPriceFoundCommand):
    direction: Literal["plus", "moins"]
