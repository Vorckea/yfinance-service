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
        self._key_locks_lock = asyncio.Lock()  # Protects access to _key_locks dict
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
        async with self._key_locks_lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._key_locks[key] = lock

        should_cleanup_lock = False
        async with lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses.inc()
                return None
            value, expiry = entry
            if expiry > self._now():
                self._hits.inc()
                return value
            # expired
            try:
                del self._cache[key]
                should_cleanup_lock = True
            except KeyError:
                pass
            self._expirations.inc()
            self._misses.inc()
            self._length.set(len(self._cache))
        
        # Clean up lock after releasing it to prevent memory leak
        if should_cleanup_lock:
            async with self._key_locks_lock:
                self._key_locks.pop(key, None)
        return None

    async def set(self, key: K, value: V) -> None:
        async with self._key_locks_lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._key_locks[key] = lock

        evicted_key = None
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
                        evicted_key = oldest
                        self._evictions.inc()
                except StopIteration:
                    pass
            self._length.set(len(self._cache))
            # count this as a put
            self._puts.inc()
        
        # Clean up the lock for the evicted key to prevent memory leak
        if evicted_key is not None:
            async with self._key_locks_lock:
                self._key_locks.pop(evicted_key, None)

    async def delete(self, key: K) -> None:
        async with self._key_locks_lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._key_locks[key] = lock

        should_cleanup_lock = False
        async with lock:
            if key in self._cache:
                self._cache.pop(key, None)
                self._length.set(len(self._cache))
                should_cleanup_lock = True
        
        # Clean up the lock for this key to prevent memory leak
        if should_cleanup_lock:
            async with self._key_locks_lock:
                self._key_locks.pop(key, None)

    async def clear(self) -> None:
        # Acquire lock on key_locks dict first
        async with self._key_locks_lock:
            # Acquire all known locks to prevent races while clearing
            locks = list(self._key_locks.values())
        
        # Acquire serially to avoid deadlocks
        for lock in locks:
            await lock.acquire()
        try:
            self._cache.clear()
            self._length.set(0)
        finally:
            for lock in locks:
                lock.release()
        
        # Clean up all locks when clearing the cache
        async with self._key_locks_lock:
            self._key_locks.clear()
