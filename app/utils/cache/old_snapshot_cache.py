import asyncio
import time
from typing import Any

from ...monitoring.metrics import (
    CACHE_INPROGRESS_LOADS,
    CACHE_LOAD_DURATION,
    CACHE_LOAD_ERRORS,
)
from .ttl_in_memory import TTLCache


class SnapshotCache:
    """Small adapter that provides `get_or_set` behavior on top of
    the primitive `TTLCache` storage.

    The TTLCache itself does not accept or await coroutines; this class
    handles coroutine lifecycles and per-key locking to prevent duplicate
    concurrent loads.
    """

    def __init__(self, maxsize: int = 32, ttl: int = 60):
        self._store: TTLCache[str, Any] = TTLCache(
            size=maxsize, ttl=ttl, cache_name="ttl_cache", resource="snapshot"
        )
        self._ttl = ttl
        self._maxsize = maxsize
        self._key_locks: dict[str, asyncio.Lock] = {}

    async def get_or_set(self, key: str, coro):
        """Return cached value if valid, else await and store new value.

        If a cached value exists we try to close the passed coroutine if it
        wasn't awaited to avoid "coroutine was never awaited" warnings.
        """
        # fast path: try to read without locking
        value = await self._store.get(key)
        if value is not None:
            try:
                if asyncio.iscoroutine(coro):
                    close_fn = getattr(coro, "close", None)
                    if close_fn:
                        close_fn()
            except Exception:
                pass
            return value

        # per-key lock to avoid duplicate concurrent loads
        lock = self._key_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._key_locks[key] = lock

        async with lock:
            # double-checked
            value = await self._store.get(key)
            if value is not None:
                try:
                    if asyncio.iscoroutine(coro):
                        close_fn = getattr(coro, "close", None)
                        if close_fn:
                            close_fn()
                except Exception:
                    pass
                return value

            # instrument the load with inflight gauge, duration histogram, and errors counter
            inflight = CACHE_INPROGRESS_LOADS.labels(cache="ttl_cache", resource="snapshot")
            hist = CACHE_LOAD_DURATION.labels(cache="ttl_cache", resource="snapshot")
            errs = CACHE_LOAD_ERRORS.labels(cache="ttl_cache", resource="snapshot")

            inflight.inc()
            start = time.monotonic()
            try:
                value = await coro
            except Exception:
                errs.inc()
                raise
            finally:
                duration = time.monotonic() - start
                try:
                    hist.observe(duration)
                except Exception:
                    pass
                inflight.dec()

            await self._store.set(key, value)
            return value
