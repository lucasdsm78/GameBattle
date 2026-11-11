from __future__ import annotations

from application.accounts.account_maintenance import AccountMaintenance
from infrastructure.runtime.periodic_task import PeriodicTask
from interface.workers.constants.worker_schedules import ACCOUNT_JANITOR_INTERVAL_SECONDS


class AccountJanitor(PeriodicTask):
    """Déclenche le ménage des comptes toutes les 10 minutes : un adaptateur d'entrée, comme une route HTTP."""

    name = "accounts.janitor"

    def __init__(self, maintenance: AccountMaintenance, *, interval_seconds: float = ACCOUNT_JANITOR_INTERVAL_SECONDS) -> None:
        super().__init__(interval_seconds=interval_seconds)
        self._maintenance = maintenance

    async def run_once(self) -> None:
        await self._maintenance.purge_expired()
