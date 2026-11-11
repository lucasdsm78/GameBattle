from __future__ import annotations

from pydantic import Field

from application.shared.commands.input_model import InputModel


class FairPriceFoundCommand(InputModel):
    # Réponses déjà jugées vues par la régie : un double appui ou un message rejoué est ignoré.
    proposals: int = Field(ge=0, le=10_000)
