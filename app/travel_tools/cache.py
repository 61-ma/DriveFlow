from __future__ import annotations

import time
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLMemoryCache(Generic[T]):
    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at <= time.time():
            self._entries.pop(key, None)
            return None
        return value

    def set(self, key: str, value: T, ttl_seconds: int) -> None:
        self._entries[key] = (time.time() + ttl_seconds, value)

