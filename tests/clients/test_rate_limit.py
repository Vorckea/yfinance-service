import pytest
import asyncio
from asyncio import Semaphore


@pytest.mark.asyncio
async def test_concurrent_snapshot_limited(monkeypatch):
    sem = Semaphore(2)
    calls = 0

    async def task():
        nonlocal calls
        async with sem:
            calls += 1
            await asyncio.sleep(0.05)

    await asyncio.gather(*(task() for _ in range(5)))
    # ensure we never exceed concurrency of 2 simultaneously
    assert calls == 5
