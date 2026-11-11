from __future__ import annotations

from dataclasses import dataclass, replace

from domain.accounts.constants.account_sessions import SESSION_RENEW_AFTER_MS, SESSION_TTL_MS


@dataclass(frozen=True, slots=True)
class PlayerSession:

    token_hash: str
    account_id: str
    expires_at_ms: int

    @classmethod
    def open(cls, token_hash: str, account_id: str, now_ms: int) -> PlayerSession:
        return cls(token_hash=token_hash, account_id=account_id, expires_at_ms=now_ms + SESSION_TTL_MS)

    def is_expired(self, now_ms: int) -> bool:
        return now_ms >= self.expires_at_ms

    def needs_renewal(self, now_ms: int) -> bool:
        return self.expires_at_ms - now_ms < SESSION_TTL_MS - SESSION_RENEW_AFTER_MS

    def renewed(self, now_ms: int) -> PlayerSession:
        return replace(self, expires_at_ms=now_ms + SESSION_TTL_MS)
