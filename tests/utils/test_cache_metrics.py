import asyncio

import pytest

from app.monitoring.metrics import (
    CACHE_INFLIGHT,
    CACHE_LOAD_DURATION,
    CACHE_LOAD_ERRORS,
    CACHE_PUTS,
)
from app.utils.cache.old_snapshot_cache import SnapshotCache


@pytest.mark.asyncio
async def test_snapshot_cache_load_metrics_success():
    cache = SnapshotCache(maxsize=2, ttl=60)

    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_fetch():
        started.set()
        await release.wait()
        return {"price": 100}

    task = asyncio.create_task(cache.get_or_set("AAPL", fake_fetch()))
    await started.wait()

    # while in-flight
    assert CACHE_INFLIGHT.labels(cache="ttl_cache", resource="snapshot")._value.get() == 1

    # allow it to finish
    release.set()
    result = await task
    assert result == {"price": 100}

    # metrics after completion
    assert CACHE_INFLIGHT.labels(cache="ttl_cache", resource="snapshot")._value.get() == 0
    # Histogram internals vary by prometheus_client version; check sum robustly
    sum_val = getattr(
        CACHE_LOAD_DURATION.labels(cache="ttl_cache", resource="snapshot"), "_sum", None
    )
    if hasattr(sum_val, "_value"):
        inner = sum_val._value
        if callable(getattr(inner, "get", None)):
            observed = inner.get()
        else:
            observed = inner
    else:
        observed = sum_val
    assert observed > 0
    assert CACHE_PUTS.labels(cache="ttl_cache", resource="snapshot")._value.get() >= 1


@pytest.mark.asyncio
async def test_snapshot_cache_load_metrics_error():
    cache = SnapshotCache(maxsize=2, ttl=60)

    started = asyncio.Event()
    release = asyncio.Event()

    async def bad_fetch():
        started.set()
        await release.wait()
        raise RuntimeError("boom")

    task = asyncio.create_task(cache.get_or_set("AAPL", bad_fetch()))
    await started.wait()

    # while in-flight
    assert CACHE_INFLIGHT.labels(cache="ttl_cache", resource="snapshot")._value.get() == 1

    # allow it to finish (and raise)
    release.set()
    with pytest.raises(RuntimeError):
        await task

    # metric expectations
    assert CACHE_INFLIGHT.labels(cache="ttl_cache", resource="snapshot")._value.get() == 0
    assert CACHE_LOAD_ERRORS.labels(cache="ttl_cache", resource="snapshot")._value.get() >= 1
    # ensure cache was not populated
    assert await cache._store.get("AAPL") is None
