import asyncio

import pytest

from app.monitoring.metrics import (
    CACHE_EVICTIONS,
    CACHE_EXPIRATIONS,
    CACHE_LENGTH,
    CACHE_PUTS,
)
from app.utils.cache.ttl_in_memory import TTLCache


@pytest.mark.asyncio
async def test_ttlcache_puts_and_eviction_metrics():
    c = TTLCache(2, ttl=60, cache_name="test_cache_puts", resource="test_puts")
    # initial puts
    await c.set("a", 1)
    await c.set("b", 2)
    await c.set("c", 3)

    # puts counted (>=3) and at least one eviction occurred
    assert CACHE_PUTS.labels(cache="test_cache_puts", resource="test_puts")._value.get() >= 3
    assert CACHE_EVICTIONS.labels(cache="test_cache_puts", resource="test_puts")._value.get() >= 1
    assert CACHE_LENGTH.labels(cache="test_cache_puts", resource="test_puts")._value.get() == 2


@pytest.mark.asyncio
async def test_ttlcache_delete_and_clear():
    c = TTLCache(4, ttl=60, cache_name="test_cache_del", resource="test_del")
    await c.set("x", 10)
    await c.set("y", 20)
    assert await c.get("x") == 10
    await c.delete("x")
    assert await c.get("x") is None
    assert CACHE_LENGTH.labels(cache="test_cache_del", resource="test_del")._value.get() == 1

    # clear while other sets may happen
    await c.set("a", 1)
    await c.set("b", 2)
    await c.clear()
    assert CACHE_LENGTH.labels(cache="test_cache_del", resource="test_del")._value.get() == 0


@pytest.mark.asyncio
async def test_ttlcache_concurrent_sets_consistency():
    c = TTLCache(3, ttl=60, cache_name="test_cache_conc", resource="test_conc")

    async def delayed_set(key, value, delay):
        await asyncio.sleep(delay)
        await c.set(key, value)

    # schedule three sets to same key with increasing delays; final value should be from max delay
    tasks = [
        asyncio.create_task(delayed_set("k", "v1", 0.05)),
        asyncio.create_task(delayed_set("k", "v2", 0.1)),
        asyncio.create_task(delayed_set("k", "v3", 0.2)),
    ]
    await asyncio.gather(*tasks)
    assert await c.get("k") == "v3"


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


@pytest.mark.asyncio
async def test_ttlcache_lock_cleanup_on_eviction():
    """Test that locks are cleaned up when keys are evicted."""
    c = TTLCache(2, ttl=60, cache_name="test_lock_evict", resource="test_lock")

    # Fill cache
    await c.set("a", 1)
    await c.set("b", 2)
    assert len(c._key_locks) == 2

    # Evict oldest key by adding a third
    await c.set("c", 3)
    # Lock for "a" should be cleaned up
    assert "a" not in c._key_locks
    assert len(c._key_locks) == 2


@pytest.mark.asyncio
async def test_ttlcache_lock_cleanup_on_deletion():
    """Test that locks are cleaned up when keys are explicitly deleted."""
    c = TTLCache(4, ttl=60, cache_name="test_lock_del", resource="test_lock_del")

    await c.set("x", 10)
    await c.set("y", 20)
    assert len(c._key_locks) == 2

    # Delete a key
    await c.delete("x")
    # Lock for "x" should be cleaned up
    assert "x" not in c._key_locks
    assert len(c._key_locks) == 1


@pytest.mark.asyncio
async def test_ttlcache_lock_cleanup_on_expiry():
    """Test that locks are cleaned up when keys expire."""
    c = TTLCache(4, ttl=0, cache_name="test_lock_exp", resource="test_lock_exp")

    await c.set("expired", 123)
    assert len(c._key_locks) == 1

    # Try to get expired key - should trigger cleanup
    result = await c.get("expired")
    assert result is None
    # Lock should be cleaned up
    assert "expired" not in c._key_locks


@pytest.mark.asyncio
async def test_ttlcache_lock_cleanup_on_clear():
    """Test that all locks are cleaned up when cache is cleared."""
    c = TTLCache(4, ttl=60, cache_name="test_lock_clear", resource="test_lock_clear")

    await c.set("a", 1)
    await c.set("b", 2)
    await c.set("c", 3)
    assert len(c._key_locks) == 3

    # Clear cache
    await c.clear()
    # All locks should be cleaned up
    assert len(c._key_locks) == 0
