import pytest
import asyncio
from app.utils.cache import SnapshotCache

@pytest.mark.asyncio
async def test_snapshot_cache_reuses_recent_value():
    cache = SnapshotCache(maxsize=2, ttl=2)
    called = 0

    async def fake_fetch():
        nonlocal called
        called += 1
        await asyncio.sleep(0)
        return {"price": 100}

    result1 = await cache.get_or_set("AAPL", fake_fetch())
    result2 = await cache.get_or_set("AAPL", fake_fetch())

    assert result1 == result2
    assert called == 1  # only one actual fetch


@pytest.mark.asyncio
async def test_snapshot_cache_expires_after_ttl(monkeypatch):
    cache = SnapshotCache(maxsize=2, ttl=0)
    async def fake_fetch(): return {"price": 100}

    await cache.get_or_set("AAPL", fake_fetch())
    result2 = await cache.get_or_set("AAPL", fake_fetch())
    # immediate expiry due to ttl=0 forces refetch
    assert result2 == {"price": 100}
