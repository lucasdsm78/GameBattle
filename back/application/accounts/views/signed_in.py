from __future__ import annotations

from dataclasses import dataclass

from application.accounts.views.account_view import AccountView


@dataclass(frozen=True, slots=True)
class SignedIn:
    """Résultat d'une inscription ou d'une connexion : le jeton en clair ne sort d'ici que vers le cookie."""

    account: AccountView
    token: str
    expires_at_ms: int
