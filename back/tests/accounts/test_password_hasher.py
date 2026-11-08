from __future__ import annotations

import asyncio

from account_support import PASSWORD

from infrastructure.security.argon2_password_hasher import Argon2PasswordHasher


def test_argon2id_hashes_are_salted_and_verified() -> None:
    hasher = Argon2PasswordHasher()

    first, second = asyncio.run(hasher.hash(PASSWORD)), asyncio.run(hasher.hash(PASSWORD))
    assert first.startswith("$argon2id$") and first != second and PASSWORD not in first
    assert asyncio.run(hasher.verify(first, PASSWORD)) is True
    assert asyncio.run(hasher.verify(first, PASSWORD + " ")) is False
    assert asyncio.run(hasher.verify(None, PASSWORD)) is False
    assert asyncio.run(hasher.verify("pas-un-hash", PASSWORD)) is False
    assert hasher.needs_rehash(first) is False
