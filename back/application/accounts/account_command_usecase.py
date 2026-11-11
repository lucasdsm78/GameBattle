from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable
from typing import Optional

from application.accounts.account_commands import CredentialsCommand
from application.accounts.account_limits import AccountLimits
from application.accounts.account_unit_of_work import AccountUnitOfWork
from application.accounts.constants.session_token_limits import SESSION_TOKEN_BYTES
from application.accounts.session_tokens import hash_session_token, is_plausible_token
from application.accounts.views.account_view import AccountView
from application.accounts.views.signed_in import SignedIn
from application.shared.attempt_limit import reserve_attempts
from application.shared.command_usecase import wall_clock_ms
from domain.accounts.models.password_policy import check_password, normalize_password
from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.player_session import PlayerSession
from domain.accounts.models.pseudo import Pseudo, check_pseudo_is_not_reserved
from domain.accounts.services.password_hasher import PasswordHasher
from exceptions import (
    InvalidAccountError,
    InvalidCredentialsError,
    PseudoAlreadyTakenError,
)


class AccountCommandUseCase:
    """Inscription, connexion, déconnexion et prolongation des sessions (la lecture est dans `AccountQueryUseCase`).

    Chaque étape qui écrit tient dans une seule unité de travail : un compte n'existe jamais sans sa session.
    Le hachage Argon2 (lent par conception) se fait entre deux transactions : aucune connexion à la base
    n'est retenue pendant le calcul.
    """

    def __init__(
        self,
        unit_of_work: Callable[[], AccountUnitOfWork],
        hasher: PasswordHasher,
        *,
        limits: AccountLimits = AccountLimits(),
        clock: Callable[[], int] = wall_clock_ms,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._hasher = hasher
        self._limits = limits
        self._clock = clock

    async def register(self, command: CredentialsCommand, client_ip: str, replacing_token: Optional[str] = None) -> SignedIn:
        now = self._clock()
        async with self._unit_of_work() as uow:
            await reserve_attempts(
                uow, now, (self._limits.attempts_per_ip, client_ip), (self._limits.signup_attempts_per_ip, client_ip)
            )
            pseudo = Pseudo.parse(command.pseudo)
            check_pseudo_is_not_reserved(pseudo)
            password = normalize_password(command.password)
            check_password(password, pseudo)
            if await uow.accounts.find_by_pseudo(pseudo) is not None:  # avant le hachage, coûteux
                raise PseudoAlreadyTakenError("Ce pseudo est déjà pris.")

        account = PlayerAccount(id=str(uuid.uuid4()), pseudo=pseudo, password_hash=await self._hasher.hash(password), created_at_ms=now)
        async with self._unit_of_work() as uow:
            await uow.accounts.add(account)  # l'index unique tranche une inscription simultanée du même pseudo
            signed_in = await self._open_session(uow, account, now, replacing_token)
            await uow.commit()
        return signed_in

    async def login(self, command: CredentialsCommand, client_ip: str, replacing_token: Optional[str] = None) -> SignedIn:
        now = self._clock()
        try:
            pseudo: Optional[Pseudo] = Pseudo.parse(command.pseudo)
        except InvalidAccountError:
            pseudo = None  # un pseudo impossible ne peut pas exister, mais la réponse reste la même
        pseudo_key = pseudo.key if pseudo else command.pseudo.casefold()
        # 1. Réserver l'essai (adresse et pseudo), validé en base avant le calcul : la limite tient sous concurrence.
        async with self._unit_of_work() as uow:
            await reserve_attempts(
                uow, now, (self._limits.attempts_per_ip, client_ip), (self._limits.login_attempts_per_pseudo, pseudo_key)
            )
            account = await uow.accounts.find_by_pseudo(pseudo) if pseudo else None

        # 2. Authentifier, hors transaction.
        password = normalize_password(command.password)
        if not await self._hasher.verify(account.password_hash if account else None, password) or account is None:
            raise InvalidCredentialsError("Pseudo ou mot de passe incorrect.")
        upgraded_hash = await self._hasher.hash(password) if self._hasher.needs_rehash(account.password_hash) else None

        # 3. Ouvrir la session.
        async with self._unit_of_work() as uow:
            await self._limits.login_attempts_per_pseudo.reset(uow.attempts, pseudo_key)
            if upgraded_hash:
                account = account.with_password_hash(upgraded_hash)
                await uow.accounts.save_password_hash(account)
            signed_in = await self._open_session(uow, account, now, replacing_token)
            await uow.commit()
        return signed_in

    async def logout(self, token: Optional[str]) -> None:
        if not is_plausible_token(token):
            return
        async with self._unit_of_work() as uow:
            await uow.sessions.delete(hash_session_token(token))
            await uow.commit()

    async def renew_session(self, token: Optional[str]) -> Optional[int]:
        """Prolonge la session d'un joueur actif ; renvoie sa nouvelle échéance, ou `None` s'il n'y avait rien à faire."""
        if not is_plausible_token(token):
            return None
        now = self._clock()
        async with self._unit_of_work() as uow:
            session = await uow.sessions.get(hash_session_token(token))
            if session is None or session.is_expired(now) or not session.needs_renewal(now):
                return None
            renewed = session.renewed(now)
            await uow.sessions.save_expiry(renewed)
            await uow.commit()
        return renewed.expires_at_ms

    async def _open_session(
        self, uow: AccountUnitOfWork, account: PlayerAccount, now_ms: int, replacing_token: Optional[str]
    ) -> SignedIn:
        """Nouvelle session ; celle que ce navigateur avait encore est révoquée dans la même transaction."""
        if is_plausible_token(replacing_token):
            await uow.sessions.delete(hash_session_token(replacing_token))
        token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        session = PlayerSession.open(hash_session_token(token), account.id, now_ms)
        await uow.sessions.add(session)
        return SignedIn(
            account=AccountView(pseudo=account.pseudo.value, account_id=account.id), token=token, expires_at_ms=session.expires_at_ms
        )

