from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, TypeGuard

from application.accounts.account_commands import CredentialsCommand
from application.accounts.attempt_limiter import AttemptLimiter
from application.shared.command_usecase import wall_clock_ms
from domain.accounts.models.password_policy import check_password, normalize_password
from domain.accounts.models.player_account import PlayerAccount
from domain.accounts.models.player_session import PlayerSession
from domain.accounts.models.pseudo import Pseudo, check_pseudo_is_not_reserved
from domain.accounts.repositories.player_account_repository import (
    PlayerAccountRepository,
)
from domain.accounts.repositories.player_session_repository import (
    PlayerSessionRepository,
)
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


@dataclass(slots=True)
class AccountLimits:
    """Freins contre le forçage : par adresse IP (tous les essais) et par pseudo (les échecs de connexion)."""

    per_ip: AttemptLimiter
    failed_logins_per_pseudo: AttemptLimiter
    signups_per_ip: AttemptLimiter

    @classmethod
    def default(cls) -> AccountLimits:
        return cls(
            per_ip=AttemptLimiter(limit=30, window_ms=15 * _MINUTE_MS),
            failed_logins_per_pseudo=AttemptLimiter(limit=5, window_ms=15 * _MINUTE_MS),
            signups_per_ip=AttemptLimiter(limit=5, window_ms=60 * _MINUTE_MS),
        )


def hash_session_token(token: str) -> str:
    # Le jeton est aléatoire (256 bits) : un SHA-256 suffit, pas besoin d'un hachage lent comme pour un mot de passe.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountUseCase:
    def __init__(
        self,
        accounts: PlayerAccountRepository,
        sessions: PlayerSessionRepository,
        hasher: PasswordHasher,
        *,
        limits: Optional[AccountLimits] = None,
        clock: Callable[[], int] = wall_clock_ms,
    ) -> None:
        self._accounts = accounts
        self._sessions = sessions
        self._hasher = hasher
        self._limits = limits or AccountLimits.default()
        self._clock = clock

    async def register(self, command: CredentialsCommand, client_ip: str) -> SignedIn:
        now = self._clock()
        self._limits.per_ip.check(client_ip, now)
        self._limits.signups_per_ip.check(client_ip, now)
        self._limits.per_ip.record(client_ip, now)
        pseudo = Pseudo.parse(command.pseudo)
        check_pseudo_is_not_reserved(pseudo)
        password = normalize_password(command.password)
        check_password(password, pseudo)
        if await self._accounts.find_by_pseudo(pseudo) is not None:
            raise PseudoAlreadyTakenError("Ce pseudo est déjà pris.")
        account = PlayerAccount(id=str(uuid.uuid4()), pseudo=pseudo, password_hash=await self._hasher.hash(password), created_at_ms=now)
        await self._accounts.add(account)
        self._limits.signups_per_ip.record(client_ip, now)
        return await self._open_session(account, now)

    async def login(self, command: CredentialsCommand, client_ip: str) -> SignedIn:
        now = self._clock()
        try:
            pseudo: Optional[Pseudo] = Pseudo.parse(command.pseudo)
        except InvalidAccountError:
            pseudo = None  # un pseudo impossible ne peut pas exister, mais la réponse reste la même
        pseudo_key = pseudo.key if pseudo else command.pseudo.casefold()
        self._limits.per_ip.check(client_ip, now)
        self._limits.failed_logins_per_pseudo.check(pseudo_key, now)
        self._limits.per_ip.record(client_ip, now)

        password = normalize_password(command.password)
        account = await self._accounts.find_by_pseudo(pseudo) if pseudo else None
        if not await self._hasher.verify(account.password_hash if account else None, password) or account is None:
            self._limits.failed_logins_per_pseudo.record(pseudo_key, now)
            raise InvalidCredentialsError("Pseudo ou mot de passe incorrect.")

        self._limits.failed_logins_per_pseudo.reset(pseudo_key)
        if self._hasher.needs_rehash(account.password_hash):
            account = account.with_password_hash(await self._hasher.hash(password))
            await self._accounts.save_password_hash(account)
        await self._sessions.delete_expired(now)
        return await self._open_session(account, now)

    async def logout(self, token: Optional[str]) -> None:
        if _plausible_token(token):
            await self._sessions.delete(hash_session_token(token))

    async def current(self, token: Optional[str]) -> CurrentPlayer:
        """Le joueur de la session, ou `NotAuthenticatedError` (jeton absent, inconnu ou expiré)."""
        if not _plausible_token(token):
            raise NotAuthenticatedError("Connecte-toi pour continuer.")
        now = self._clock()
        token_hash = hash_session_token(token)
        session = await self._sessions.get(token_hash)
        if session is not None and session.is_expired(now):
            await self._sessions.delete(token_hash)
            session = None
        account = await self._accounts.get(session.account_id) if session else None
        if session is None or account is None:
            raise NotAuthenticatedError("Connecte-toi pour continuer.")
        view = AccountView(pseudo=account.pseudo.value)
        if not session.needs_renewal(now):
            return CurrentPlayer(view)
        renewed = session.renewed(now)
        await self._sessions.save_expiry(renewed)
        return CurrentPlayer(view, renewed_until_ms=renewed.expires_at_ms)

    async def _open_session(self, account: PlayerAccount, now_ms: int) -> SignedIn:
        token = secrets.token_urlsafe(SESSION_TOKEN_BYTES)
        session = PlayerSession.open(hash_session_token(token), account.id, now_ms)
        await self._sessions.add(session)
        return SignedIn(account=AccountView(pseudo=account.pseudo.value), token=token, expires_at_ms=session.expires_at_ms)


def _plausible_token(token: Optional[str]) -> TypeGuard[str]:
    return bool(token) and len(token) <= MAX_SESSION_TOKEN_LENGTH
