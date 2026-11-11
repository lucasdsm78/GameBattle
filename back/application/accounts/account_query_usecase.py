from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from application.accounts.account_unit_of_work import AccountUnitOfWork
from application.accounts.session_tokens import hash_session_token, is_plausible_token
from application.accounts.views.account_view import AccountView
from application.accounts.views.current_player import CurrentPlayer
from application.shared.command_usecase import wall_clock_ms
from exceptions import NotAuthenticatedError


class AccountQueryUseCase:
    """Qui est connecté : lecture seule, appelée à chaque requête authentifiée et par le temps réel.

    Rien n'est écrit ici. Une session expirée est simplement refusée (le ménage la supprimera), et la
    prolongation d'une session active est une commande à part (`AccountCommandUseCase.renew_session`).
    """

    def __init__(self, unit_of_work: Callable[[], AccountUnitOfWork], *, clock: Callable[[], int] = wall_clock_ms) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def current(self, token: Optional[str]) -> CurrentPlayer:
        """Le joueur de la session, ou `NotAuthenticatedError` (jeton absent, inconnu ou expiré)."""
        if not is_plausible_token(token):
            raise NotAuthenticatedError("Connecte-toi pour continuer.")
        now = self._clock()
        async with self._unit_of_work() as uow:
            session = await uow.sessions.get(hash_session_token(token))
            account = await uow.accounts.get(session.account_id) if session and not session.is_expired(now) else None
        if session is None or account is None:
            raise NotAuthenticatedError("Connecte-toi pour continuer.")
        return CurrentPlayer(AccountView(pseudo=account.pseudo.value, account_id=account.id), renewal_due=session.needs_renewal(now))
