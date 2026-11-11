from __future__ import annotations

from typing import Annotated

from pydantic import Field

# Positions audio issues des lecteurs natifs : un flottant entier (ex. 12000.0) reste accepté.
DurationMs = Annotated[int, Field(ge=0, le=24 * 60 * 60 * 1000, strict=False)]
