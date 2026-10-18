from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ClientMessage(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    type: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9.-]+$")
    payload: Optional[dict[str, Any]] = None
