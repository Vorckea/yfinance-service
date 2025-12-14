import asyncio
import time
from typing import Generic, Optional

from ...monitoring.metrics import (
    CACHE_EVICTIONS,
    CACHE_EXPIRATIONS,
    CACHE_HITS,
    CACHE_LENGTH,
    CACHE_MISSES,
    CACHE_PUTS,
)
from .interface import CacheInterface, K, V


class TTLCache(CacheInterface, Generic[K, V]):
    def __init__(
        self, size: int, ttl: int, *, cache_name: str = "ttl_cache", resource: str = "generic"
    ) -> None:
        self.size = size
        self.ttl = ttl
        self._cache_name = cache_name
        self._resource = resource
        self._key_locks: dict[K, asyncio.Lock] = {}
        self._cache: dict[K, tuple[V, float]] = {}

        # Labeled metric children for this cache instance
        self._hits = CACHE_HITS.labels(cache=self._cache_name, resource=self._resource)
        self._misses = CACHE_MISSES.labels(cache=self._cache_name, resource=self._resource)
        self._evictions = CACHE_EVICTIONS.labels(cache=self._cache_name, resource=self._resource)
        self._expirations = CACHE_EXPIRATIONS.labels(
            cache=self._cache_name, resource=self._resource
        )
        self._length = CACHE_LENGTH.labels(cache=self._cache_name, resource=self._resource)
        self._puts = CACHE_PUTS.labels(cache=self._cache_name, resource=self._resource)
        # Ensure gauge reflects initial state
        self._length.set(0)

    def _now(self) -> float:
        # monotonic clock is immune to system clock changes
        return time.monotonic()

    async def get(self, key: K) -> Optional[V]:
        # Per-key locking prevents races with concurrent sets/deletes
        lock = self._key_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._key_locks[key] = lock

        async with lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses.inc()
                return None
            value, expiry = entry
            if expiry >= self._now():
                self._hits.inc()
                return value
            # expired
            try:
                del self._cache[key]
            except KeyError:
                # Key may have already been removed by another coroutine; safe to ignore
                pass
            self._expirations.inc()
            self._misses.inc()
            self._length.set(len(self._cache))
            return None

    async def set(self, key: K, value: V) -> None:
        lock = self._key_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._key_locks[key] = lock

        async with lock:
            expiry = self._now() + self.ttl
            self._cache[key] = (value, expiry)
            # enforce max size by evicting oldest insertion
            if len(self._cache) > self.size:
                try:
                    oldest = next(iter(self._cache))
                    # avoid counting an eviction of the key we just set
                    if oldest != key:
                        del self._cache[oldest]
                        self._evictions.inc()
                except StopIteration:
                    pass
            self._length.set(len(self._cache))
            # count this as a put
            self._puts.inc()

    async def delete(self, key: K) -> None:
        lock = self._key_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._key_locks[key] = lock

        async with lock:
            self._cache.pop(key, None)
            self._length.set(len(self._cache))

    async def clear(self) -> None:
        # Acquire all known locks to prevent races while clearing
        locks = list(self._key_locks.values())
        # Acquire serially to avoid deadlocks
        for l in locks:
            await l.acquire()
        try:
            self._cache.clear()
            self._length.set(0)
        finally:
            for l in locks:
                l.release()
