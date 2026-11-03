from __future__ import annotations

from collections import deque

from exceptions import TooManyAttemptsError


class AttemptLimiter:

    def __init__(self, limit: int, window_ms: int, max_keys: int = 10_000) -> None:
        self._limit = limit
        self._window_ms = window_ms
        self._max_keys = max_keys
        self._attempts: dict[str, deque[int]] = {}

    def check(self, key: str, now_ms: int) -> None:
        attempts = self._recent(key, now_ms)
        if len(attempts) >= self._limit:
            raise TooManyAttemptsError(retry_after_seconds=-(-(attempts[0] + self._window_ms - now_ms) // 1000))

    def record(self, key: str, now_ms: int) -> None:
        attempts = self._recent(key, now_ms)
        if not attempts:
            self._attempts.pop(key, None)  # réinsérée en fin : l'ordre du dict reste celui de l'activité
            if len(self._attempts) >= self._max_keys:
                del self._attempts[next(iter(self._attempts))]
            self._attempts[key] = attempts
        attempts.append(now_ms)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def _recent(self, key: str, now_ms: int) -> deque[int]:
        attempts = self._attempts.get(key, deque())
        while attempts and attempts[0] <= now_ms - self._window_ms:
            attempts.popleft()
        return attempts
