import pytest

from app.utils.helpers import fetch_with_cache, normalize_symbol


class InMemoryCache:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value):
        self.store[key] = value


def test_normalize_symbol_basic():
    assert normalize_symbol(None) == ""
    assert normalize_symbol("") == ""
    assert normalize_symbol(" aapl ") == "AAPL"
    assert normalize_symbol(" ApPl ") == "APPL"


@pytest.mark.asyncio
async def test_fetch_with_cache_miss_and_set():
    cache = InMemoryCache()

    async def fetcher():
        return {"x": 1}

    res = await fetch_with_cache("k", cache, fetcher)
    assert res == {"x": 1}
    assert await cache.get("k") == {"x": 1}


@pytest.mark.asyncio
async def test_fetch_with_cache_hit():
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
    cache = InMemoryCache()

    async def fetcher():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await fetch_with_cache("k", cache, fetcher)

    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_fetch_with_cache_ttl_param_unused():
    cache = InMemoryCache()

    async def fetcher():
        return "v"

    res = await fetch_with_cache("k2", cache, fetcher, ttl=5)
    assert res == "v"
    assert await cache.get("k2") == "v"


@pytest.mark.asyncio
async def test_fetch_with_cache_uses_set_with_ttl():
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
