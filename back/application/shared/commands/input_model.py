from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class InputModel(BaseModel):
    """Entrée client : types stricts, champs inconnus refusés, espaces superflus retirés."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True, frozen=True)
