"""Qui peut trouver un salon."""

from __future__ import annotations

from enum import StrEnum


class RoomVisibility(StrEnum):
    PUBLIC = "public"  # listé pour tous
    PRIVATE = "private"  # seulement par son lien d'invitation
