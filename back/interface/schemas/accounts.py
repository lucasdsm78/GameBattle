from __future__ import annotations

from pydantic import BaseModel


class AccountResponse(BaseModel):
    pseudo: str
