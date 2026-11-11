from __future__ import annotations

from dataclasses import dataclass

from application.shared.attempt_limit import AttemptLimit

_MINUTE_MS = 60_000


@dataclass(frozen=True, slots=True)
class AccountLimits:
    """Freins contre le forçage. Chaque essai est réservé dès sa réception, avant toute validation et avant
    Argon2 : refusé, invalide ou réussi, il compte. Une connexion réussie remet à zéro le compteur du pseudo."""

    attempts_per_ip: AttemptLimit = AttemptLimit("ip", limit=30, window_ms=15 * _MINUTE_MS)
    login_attempts_per_pseudo: AttemptLimit = AttemptLimit("login", limit=5, window_ms=15 * _MINUTE_MS)
    signup_attempts_per_ip: AttemptLimit = AttemptLimit("signup", limit=10, window_ms=60 * _MINUTE_MS)

    @property
    def longest_window_ms(self) -> int:
        return max(limit.window_ms for limit in (self.attempts_per_ip, self.login_attempts_per_pseudo, self.signup_attempts_per_ip))
