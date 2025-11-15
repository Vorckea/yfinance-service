"""In-memory TTL-based async-safe cache for snapshot responses."""

import asyncio
import time
from collections import OrderedDict


class SnapshotCache:
    """Simple TTL-based async-safe in-memory cache for snapshot responses."""

    def __init__(self, maxsize: int = 32, ttl: int = 60):
        """Initialize the cache."""
        self._cache = OrderedDict()
        self._ttl = ttl
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, coro):
        """Return cached value if valid, else await and store new value."""
        now = time.time()
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry > now:
                    # If caller passed a coroutine object which was not awaited
                    # because we can return a cached value, close it to avoid
                    # "coroutine was never awaited" warnings.
                    try:
                        if asyncio.iscoroutine(coro):
                            close_fn = getattr(coro, "close", None)
                            if close_fn:
                                close_fn()
                    except Exception:
                        # Be defensive: closing is best-effort and must not
                        # interfere with normal cache behavior.
                        pass
                    return value
                del self._cache[key]

            # Fetch new value and store
            value = await coro
            self._cache[key] = (value, now + self._ttl)
            if len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)
            return value
