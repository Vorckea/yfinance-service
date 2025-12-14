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
    observed_values = []

    async def delayed_set(key, value, delay):
        await asyncio.sleep(delay)
        await c.set(key, value)
        # Record that this value was successfully written
        observed_values.append(value)

    async def concurrent_getter(key, check_delay):
        """Continuously get the key during concurrent sets to verify consistency."""
        await asyncio.sleep(check_delay)
        val = await c.get(key)
        # Any value we get should be one of the values we're writing
        if val is not None:
            assert val in ["v1", "v2", "v3"], f"Unexpected value during concurrent access: {val}"
        return val

    # Schedule three sets to same key with increasing delays
    set_tasks = [
        asyncio.create_task(delayed_set("k", "v1", 0.05)),
        asyncio.create_task(delayed_set("k", "v2", 0.1)),
        asyncio.create_task(delayed_set("k", "v3", 0.2)),
    ]
    # Schedule gets that happen during the sets to verify locking prevents inconsistent reads
    get_tasks = [
        asyncio.create_task(concurrent_getter("k", 0.06)),  # After v1 should be set
        asyncio.create_task(concurrent_getter("k", 0.11)),  # After v2 should be set
        asyncio.create_task(concurrent_getter("k", 0.21)),  # After v3 should be set
    ]

    await asyncio.gather(*set_tasks, *get_tasks)

    # Verify all intermediate values were written
    assert len(observed_values) == 3, "Not all set operations completed"
    assert "v1" in observed_values, "First value was not written"
    assert "v2" in observed_values, "Second value was not written"
    assert "v3" in observed_values, "Third value was not written"

    # Final value should be from last write (highest delay)
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
