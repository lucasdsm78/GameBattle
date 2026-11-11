from __future__ import annotations

from dataclasses import dataclass

from application.accounts.views.account_view import AccountView


@dataclass(frozen=True, slots=True)
class CurrentPlayer:
    """Le joueur de la session. `renewal_due` : la session est assez ancienne pour être prolongée (une écriture,
    demandée à part à `AccountCommandUseCase.renew_session`)."""

    account: AccountView
    renewal_due: bool = False
