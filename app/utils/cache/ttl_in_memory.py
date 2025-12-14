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
    """
    An in-memory cache with time-to-live (TTL) expiration and FIFO eviction policy.

    This cache evicts the oldest inserted item when the maximum size is reached,
    following a FIFO (first-in, first-out) policy. It does not implement a
    least-recently-used (LRU) eviction strategy.

    The eviction order relies on the insertion order of Python's built-in dict,
    which is guaranteed to be preserved in Python 3.7 and later.

    Thread-safety is ensured for asynchronous use cases by protecting all cache
    operations with an asyncio.Lock.

    The `cache_name` and `resource` parameters are used to label Prometheus metrics
    for cache hits, misses, evictions, expirations, length, and puts, allowing
    for fine-grained monitoring of cache usage and performance.
    """
    def __init__(
        self, size: int, ttl: int, *, cache_name: str = "ttl_cache", resource: str = "generic"
    ) -> None:
        self.size = size
        self.ttl = ttl
        self._cache_name = cache_name
        self._resource = resource
        self._lock = asyncio.Lock()
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
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses.inc()
                return None
            value, expiry = entry
            if expiry > self._now():
                self._hits.inc()
                return value
            # expired
            del self._cache[key]
            self._expirations.inc()
            self._misses.inc()
            self._length.set(len(self._cache))
            return None

    async def set(self, key: K, value: V) -> None:
        async with self._lock:
            # enforce max size by evicting oldest entry before inserting new key
            if key not in self._cache and len(self._cache) >= self.size:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
                self._evictions.inc()
            expiry = self._now() + self.ttl
            self._cache[key] = (value, expiry)
            self._length.set(len(self._cache))
            self._puts.inc()

    async def delete(self, key: K) -> None:
        async with self._lock:
            if self._cache.pop(key, None) is not None:
                self._length.set(len(self._cache))

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
            self._length.set(0)
