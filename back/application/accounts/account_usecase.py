from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, TypeGuard

from application.accounts.account_commands import CredentialsCommand
from application.accounts.account_unit_of_work import AccountUnitOfWork
from application.accounts.attempt_counter import AttemptLimit
from application.shared.command_usecase import wall_clock_ms
from domain.accounts.models.password_policy import check_password, normalize_password
from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.player_session import PlayerSession
from domain.accounts.models.pseudo import Pseudo, check_pseudo_is_not_reserved
from domain.accounts.services.password_hasher import PasswordHasher
from exceptions import (
    InvalidAccountError,
    InvalidCredentialsError,
    NotAuthenticatedError,
    PseudoAlreadyTakenError,
)

SESSION_TOKEN_BYTES = 32
MAX_SESSION_TOKEN_LENGTH = 128
_MINUTE_MS = 60_000


@dataclass(frozen=True, slots=True)
class AccountView:
    pseudo: str


@dataclass(frozen=True, slots=True)
class CurrentPlayer:
    """Le joueur de la session ; `renewed_until_ms` est renseigné quand la session vient d'être prolongée."""

    account: AccountView
    renewed_until_ms: Optional[int] = None


@dataclass(frozen=True, slots=True)
class SignedIn:
    """Résultat d'une inscription ou d'une connexion : le jeton en clair ne sort d'ici que vers le cookie."""

    account: AccountView
    token: str
    expires_at_ms: int


@dataclass(frozen=True, slots=True)
class AccountLimits:
    """Freins contre le forçage : par adresse IP (tous les essais) et par pseudo (les échecs de connexion)."""

    attempts_per_ip: AttemptLimit = AttemptLimit("ip", limit=30, window_ms=15 * _MINUTE_MS)
    failed_logins_per_pseudo: AttemptLimit = AttemptLimit("login", limit=5, window_ms=15 * _MINUTE_MS)
    signups_per_ip: AttemptLimit = AttemptLimit("signup", limit=5, window_ms=60 * _MINUTE_MS)

    @property
    def longest_window_ms(self) -> int:
        return max(limit.window_ms for limit in (self.attempts_per_ip, self.failed_logins_per_pseudo, self.signups_per_ip))


def hash_session_token(token: str) -> str:
    # Le jeton est aléatoire (256 bits) : un SHA-256 suffit, pas besoin d'un hachage lent comme pour un mot de passe.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountUseCase:
    """Inscription, connexion et sessions.

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
            await self._limits.attempts_per_ip.count_attempt(uow.attempts, client_ip, now)
            await self._limits.signups_per_ip.ensure_allowed(uow.attempts, client_ip, now)
            await uow.commit()  # l'essai compte même si la demande est refusée ensuite
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
            await self._limits.signups_per_ip.record(uow.attempts, client_ip, now)
            await uow.commit()
        return signed_in

    async def login(self, command: CredentialsCommand, client_ip: str, replacing_token: Optional[str] = None) -> SignedIn:
        now = self._clock()
        try:
            pseudo: Optional[Pseudo] = Pseudo.parse(command.pseudo)
        except InvalidAccountError:
            pseudo = None  # un pseudo impossible ne peut pas exister, mais la réponse reste la même
        pseudo_key = pseudo.key if pseudo else command.pseudo.casefold()
        async with self._unit_of_work() as uow:
            await self._limits.attempts_per_ip.count_attempt(uow.attempts, client_ip, now)
            await self._limits.failed_logins_per_pseudo.ensure_allowed(uow.attempts, pseudo_key, now)
            await uow.commit()
            account = await uow.accounts.find_by_pseudo(pseudo) if pseudo else None

        password = normalize_password(command.password)
        if not await self._hasher.verify(account.password_hash if account else None, password) or account is None:
            async with self._unit_of_work() as uow:
                await self._limits.failed_logins_per_pseudo.record(uow.attempts, pseudo_key, now)
                await uow.commit()
            raise InvalidCredentialsError("Pseudo ou mot de passe incorrect.")

        upgraded_hash = await self._hasher.hash(password) if self._hasher.needs_rehash(account.password_hash) else None
        async with self._unit_of_work() as uow:
            await self._limits.failed_logins_per_pseudo.reset(uow.attempts, pseudo_key)
            if upgraded_hash:
                account = account.with_password_hash(upgraded_hash)
                await uow.accounts.save_password_hash(account)
            await uow.sessions.delete_expired(now)
            await uow.attempts.purge(started_before_ms=now - self._limits.longest_window_ms)
            signed_in = await self._open_session(uow, account, now, replacing_token)
            await uow.commit()
        return signed_in

    async def logout(self, token: Optional[str]) -> None:
        if not _plausible_token(token):
            return
        async with self._unit_of_work() as uow:
            await uow.sessions.delete(hash_session_token(token))
            await uow.commit()

    async def current(self, token: Optional[str]) -> CurrentPlayer:
        """Le joueur de la session, ou `NotAuthenticatedError` (jeton absent, inconnu ou expiré)."""
        if not _plausible_token(token):
            raise NotAuthenticatedError("Connecte-toi pour continuer.")
        now = self._clock()
        token_hash = hash_session_token(token)
        async with self._unit_of_work() as uow:
            session = await uow.sessions.get(token_hash)
            if session is not None and session.is_expired(now):
                await uow.sessions.delete(token_hash)
                await uow.commit()
                session = None
            account = await uow.accounts.get(session.account_id) if session else None
            if session is None or account is None:
                raise NotAuthenticatedError("Connecte-toi pour continuer.")
            view = AccountView(pseudo=account.pseudo.value)
            if not session.needs_renewal(now):
                return CurrentPlayer(view)
            renewed = session.renewed(now)
            await uow.sessions.save_expiry(renewed)
            await uow.commit()
        return CurrentPlayer(view, renewed_until_ms=renewed.expires_at_ms)

    async def _open_session(
        self, uow: AccountUnitOfWork, account: PlayerAccount, now_ms: int, replacing_token: Optional[str]
    ) -> SignedIn:
        """Nouvelle session ; celle que ce navigateur avait encore est révoquée dans la même transaction."""
        if _plausible_token(replacing_token):
            await uow.sessions.delete(hash_session_token(replacing_token))
        token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        session = PlayerSession.open(hash_session_token(token), account.id, now_ms)
        await uow.sessions.add(session)
        return SignedIn(account=AccountView(pseudo=account.pseudo.value), token=token, expires_at_ms=session.expires_at_ms)


def _plausible_token(token: Optional[str]) -> TypeGuard[str]:
    return bool(token) and len(token) <= MAX_SESSION_TOKEN_LENGTH
