from __future__ import annotations

from dataclasses import dataclass, replace

from domain.accounts.models.pseudo import Pseudo


@dataclass(frozen=True, slots=True)
class PlayerAccount:

    id: str
    pseudo: Pseudo
    password_hash: str
    created_at_ms: int

    def with_password_hash(self, password_hash: str) -> PlayerAccount:
        return replace(self, password_hash=password_hash)
