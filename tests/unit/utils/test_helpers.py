"""Unit tests for `app.utils.helpers`."""

import pytest

from app.utils.helpers import fetch_with_cache, normalize_symbol


class InMemoryCache:
    """A simple in-memory cache implementation for testing purposes."""

    def __init__(self):
        """Initialize a simple in-memory cache for testing purposes."""
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value


def test_normalize_symbol_basic():
    """Test that `normalize_symbol` trims whitespace and converts to uppercase."""
    assert normalize_symbol(None) == ""
    assert normalize_symbol("") == ""
    assert normalize_symbol(" aapl ") == "AAPL"
    assert normalize_symbol(" ApPl ") == "APPL"


@pytest.mark.asyncio
async def test_fetch_with_cache_miss_and_set():
    """Test that if the cache does not have a value, the fetcher is called, the result is cached, and returned."""
    cache = InMemoryCache()

    async def fetcher():
        return {"x": 1}

    res = await fetch_with_cache("k", cache, fetcher)
    assert res == {"x": 1}
    assert await cache.get("k") == {"x": 1}


@pytest.mark.asyncio
async def test_fetch_with_cache_hit():
    """Test that if the cache has a value, the fetcher is not called and the cached value is returned."""
    cache = InMemoryCache()
    await cache.set("k", 42)

    called = False

    async def fetcher():
        nonlocal called
        called = True
        return 0

    res = await fetch_with_cache("k", cache, fetcher)
    assert res == 42
    assert not called


@pytest.mark.asyncio
async def test_fetch_with_cache_fetcher_exception():
    """Test that if the fetcher raises an exception, the cache is not updated."""
    cache = InMemoryCache()

    async def fetcher():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await fetch_with_cache("k", cache, fetcher)

    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_fetch_with_cache_ttl_param_unused():
    """Test that `fetch_with_cache` does not raise an error if `ttl` is provided.

    The cache implementation used in the test does not support TTL.
    """
    cache = InMemoryCache()

    async def fetcher():
        return "v"

    res = await fetch_with_cache("k2", cache, fetcher, ttl=5)
    assert res == "v"
    assert await cache.get("k2") == "v"


@pytest.mark.asyncio
async def test_fetch_with_cache_uses_set_with_ttl():
    """Test that `fetch_with_cache` calls `set_with_ttl` if available on the cache."""

    class TTLCacheStub:
        def __init__(self):
            self.store = {}
            self.called = False
            self.args = None

        async def get(self, key):
            return self.store.get(key)

        async def set_with_ttl(self, key, value, ttl):
            self.called = True
            self.args = (key, value, ttl)
            self.store[key] = value

    cache = TTLCacheStub()

    async def fetcher():
        return "ttl-value"

    res = await fetch_with_cache("kt", cache, fetcher, ttl=123)
    assert res == "ttl-value"
    assert cache.called
    assert cache.args == ("kt", "ttl-value", 123)
    assert await cache.get("kt") == "ttl-value"
