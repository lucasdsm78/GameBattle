from __future__ import annotations

import asyncio
from typing import Optional

from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError

from domain.accounts.services.password_hasher import PasswordHasher

MAX_CONCURRENT_HASHES = 2


class Argon2PasswordHasher(PasswordHasher):

    def __init__(self, hasher: Optional[Argon2Hasher] = None, max_concurrent: int = MAX_CONCURRENT_HASHES) -> None:
        self._hasher = hasher or Argon2Hasher()
        self._slots = asyncio.Semaphore(max_concurrent)
        self._decoy_hash = self._hasher.hash("gamebattle-compte-inconnu")

    async def hash(self, password: str) -> str:
        async with self._slots:
            return await asyncio.to_thread(self._hasher.hash, password)

    async def verify(self, password_hash: Optional[str], password: str) -> bool:
        async with self._slots:
            matches = await asyncio.to_thread(self._verify, password_hash or self._decoy_hash, password)
        return matches and password_hash is not None

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)

    def _verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False
