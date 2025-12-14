import pytest

from app.monitoring.metrics import (
    CACHE_EXPIRATIONS,
    CACHE_LENGTH,
)
from app.utils.cache.ttl_in_memory import TTLCache


@pytest.mark.asyncio
async def test_ttlcache_set_get_and_eviction():
    c = TTLCache(2, ttl=60, cache_name="test_cache", resource="test")
    await c.set("a", 1)
    await c.set("b", 2)
    # both present
    assert await c.get("a") == 1
    assert await c.get("b") == 2

    # add third causes eviction of oldest ("a")
    await c.set("c", 3)
    assert await c.get("a") is None
    assert await c.get("b") == 2
    assert await c.get("c") == 3

    # gauge should report length 2
    assert CACHE_LENGTH.labels(cache="test_cache", resource="test")._value.get() == 2


@pytest.mark.asyncio
async def test_ttlcache_expiry_and_metrics():
    c = TTLCache(2, ttl=0, cache_name="test_cache2", resource="test2")
    await c.set("x", 42)
    # immediate expiry
    assert await c.get("x") is None
    # expiration counter incremented
    assert CACHE_EXPIRATIONS.labels(cache="test_cache2", resource="test2")._value.get() >= 1
