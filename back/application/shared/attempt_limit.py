from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from application.shared.attempt_counter import AttemptCounter, AttemptWindow
from exceptions import TooManyAttemptsError


@dataclass(frozen=True, slots=True)
class Reservation:
    limit: int
    window: AttemptWindow

    @property
    def exceeded(self) -> bool:
        return self.window.count > self.limit


@dataclass(frozen=True, slots=True)
class AttemptLimit:
    """Au plus `limit` essais par `window_ms` pour un même sujet (adresse IP, pseudo…) dans une portée donnée."""

    scope: str
    limit: int
    window_ms: int

    async def reserve(self, counter: AttemptCounter, subject: str, now_ms: int) -> Reservation:
        return Reservation(self.limit, await counter.hit(self.scope, subject, now_ms, self.window_ms))

    async def reset(self, counter: AttemptCounter, subject: str) -> None:
        await counter.reset(self.scope, subject)


def enforce(now_ms: int, *reservations: Reservation) -> None:
    """Refuse si une des réservations dépasse sa limite ; l'attente annoncée est celle de la plus longue."""
    exceeded = [reservation.window.resets_at_ms for reservation in reservations if reservation.exceeded]
    if exceeded:
        raise TooManyAttemptsError(retry_after_seconds=max(1, -(-(max(exceeded) - now_ms) // 1000)))


class AttemptUnitOfWork(Protocol):
    """Ce qu'il faut pour réserver des essais : le compteur et la validation de sa transaction."""

    attempts: AttemptCounter

    async def commit(self) -> None: ...


async def reserve_attempts(uow: AttemptUnitOfWork, now_ms: int, *limits: tuple[AttemptLimit, str]) -> None:
    """Compte l'essai dans chaque limite et le valide en base, puis refuse si l'une est dépassée.

    La validation précède le refus : une requête bloquée compte aussi, et une rafale ne se recharge pas.
    """
    reservations = [await limit.reserve(uow.attempts, subject, now_ms) for limit, subject in limits]
    await uow.commit()
    enforce(now_ms, *reservations)
