from __future__ import annotations

from collections.abc import Callable

from application.shared.outbox import OutboxNotifier
from interface.workers.outbox_relay import OutboxRelay


class RelayNotifier(OutboxNotifier):
    """Réveille le relais, résolu à l'usage : le cas d'usage n'a pas à connaître le relais à sa construction."""

    def __init__(self, relay: Callable[[], OutboxRelay]) -> None:
        self._relay = relay

    def notify(self) -> None:
        self._relay().wake()
