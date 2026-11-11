"""Lecture du blindtest : états et commandes du lecteur."""

from __future__ import annotations

PLAYBACK_STATES = frozenset({"stopped", "playing", "paused"})
PLAYBACK_ACTIONS = frozenset({"play", "pause", "resume", "stop", "seek"})
