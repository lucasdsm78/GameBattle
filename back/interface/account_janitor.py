from __future__ import annotations

from application.accounts.account_usecase import AccountUseCase
from interface.periodic_task import PeriodicTask

JANITOR_INTERVAL_SECONDS = 10 * 60


class AccountJanitor(PeriodicTask):
    """Toutes les 10 minutes : sessions expirées et compteurs d'essais périmés quittent la base."""

    name = "accounts.janitor"

    def __init__(self, accounts: AccountUseCase, *, interval_seconds: float = JANITOR_INTERVAL_SECONDS) -> None:
        super().__init__(interval_seconds=interval_seconds)
        self._accounts = accounts

    async def run_once(self) -> None:
        await self._accounts.purge_expired()
