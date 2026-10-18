from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SevenDifference:
    id: str
    label: str
