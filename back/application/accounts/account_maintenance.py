from __future__ import annotations

from collections.abc import Callable

from application.accounts.account_unit_of_work import AccountUnitOfWork
from application.accounts.account_usecase import AccountLimits
from application.shared.command_usecase import wall_clock_ms


class AccountMaintenance:
    """Ménage des comptes : sessions expirées et compteurs d'essais dont la fenêtre est close quittent la base."""

    def __init__(
        self,
        unit_of_work: Callable[[], AccountUnitOfWork],
        *,
        limits: AccountLimits = AccountLimits(),
        clock: Callable[[], int] = wall_clock_ms,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._limits = limits
        self._clock = clock

    async def purge_expired(self) -> None:
        now = self._clock()
        async with self._unit_of_work() as uow:
            await uow.sessions.delete_expired(now)
            await uow.attempts.purge(started_before_ms=now - self._limits.longest_window_ms)
            await uow.commit()
