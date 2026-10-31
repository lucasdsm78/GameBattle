from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GameRules:
    """Ce que l'écran des règles affiche avant une manche : trois lignes et un exemple."""

    lines: tuple[str, str, str]
    example: str


def seconds(ms: int) -> int:
    return ms // 1000
