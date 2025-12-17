import asyncio

import pytest

from app.utils.cache.old_snapshot_cache import SnapshotCache
from app.utils.cache.ttl_in_memory import TTLCache


@pytest.mark.asyncio
async def test_ttlcache_concurrent_access():
    """Test that concurrent operations are properly serialized by the lock."""
    cache = TTLCache(10, ttl=60, cache_name="test_concurrent", resource="test")

    async def writer(key: str, value: int):
        await cache.set(key, value)

    async def reader(key: str):
        return await cache.get(key)

    # Run multiple concurrent operations
    await asyncio.gather(
        writer("a", 1),
        writer("b", 2),
        writer("c", 3),
        reader("a"),
        reader("b"),
    )

    # Verify final state is consistent
    assert await cache.get("a") == 1
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3

    # Clear should work correctly
    await cache.clear()
    assert await cache.get("a") is None


@pytest.mark.asyncio
async def test_snapshotcache_lock_cleanup_on_success_and_error():
    sc = SnapshotCache(maxsize=4, ttl=60)

    async def make_value():
        await asyncio.sleep(0)
        return 123

    async def make_error():
        await asyncio.sleep(0)
        raise RuntimeError("boom")

    # success
    v = await sc.get_or_set("k1", make_value())
    assert v == 123
    assert "k1" not in sc._key_locks

    # error path should also clean up locks
    with pytest.raises(RuntimeError):
        await sc.get_or_set("k2", make_error())
    assert "k2" not in sc._key_locks
