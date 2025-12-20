import httpx
import pytest

from app.dependencies import get_info_cache, get_yfinance_client
from app.main import app
from app.utils.cache import TTLCache
from tests.clients.fake_client import FakeYFinanceClient


@pytest.mark.asyncio
@pytest.mark.integration
async def test_snapshot_returns_complete_data():
    """Integration test: verify snapshot endpoint returns all required fields."""
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/snapshot/AAPL")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify top-level fields
        assert data["symbol"] == "AAPL"
        assert "current_price" in data
        assert "currency" in data
        assert data["current_price"] == 123.45
        assert data["currency"] == "USD"

        # Verify nested objects exist
        assert "info" in data
        assert "quote" in data

        # Verify info contains expected fields
        info = data["info"]
        assert info["symbol"] == "AAPL"
        assert info["short_name"] == "Fake Company Inc."
        assert info["currency"] == "USD"

        # Verify quote contains expected fields
        quote = data["quote"]
        assert quote["symbol"] == "AAPL"
        assert quote["current_price"] == 123.45
        assert quote["previous_close"] == 122.00
        assert quote["open_price"] == 123.00
        assert quote["high"] == 124.00
        assert quote["low"] == 121.50
        assert quote["volume"] == 1_000_000

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_snapshot_info_caching():
    """Integration test: verify info is cached and quote is fetched fresh on each request."""
    call_counts = {"get_info": 0}

    class CountingFakeClient(FakeYFinanceClient):
        async def get_info(self, symbol: str):
            call_counts["get_info"] += 1
            return await super().get_info(symbol)

    counting_client = CountingFakeClient()
    # Use a shared cache instance for this test
    info_cache = TTLCache(size=32, ttl=60, cache_name="test_cache", resource="snapshot")

    app.dependency_overrides[get_yfinance_client] = lambda: counting_client
    app.dependency_overrides[get_info_cache] = lambda: info_cache

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First request: fetch snapshot
        resp1 = await client.get("/snapshot/AAPL")
        assert resp1.status_code == 200
        # Note: get_info is called twice - once for info, once for quote extraction
        assert call_counts["get_info"] == 2, "Info should be fetched for both info and quote"

        # Second request: info should be cached, but quote still calls get_info
        resp2 = await client.get("/snapshot/AAPL")
        assert resp2.status_code == 200
        assert call_counts["get_info"] == 3, "Info cached but quote still fetches"

        # Third request for different symbol: should call get_info again (twice)
        resp3 = await client.get("/snapshot/MSFT")
        assert resp3.status_code == 200
        assert call_counts["get_info"] == 5, "Info should be fetched twice for new symbol"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_snapshot_error_propagation():
    """Integration test: 502 error from info or quote should propagate."""

    class FailingFakeClient(FakeYFinanceClient):
        async def get_info(self, symbol: str):
            from fastapi import HTTPException

            raise HTTPException(status_code=502, detail="Upstream error")

    failing_client = FailingFakeClient()
    app.dependency_overrides[get_yfinance_client] = lambda: failing_client

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/snapshot/AAPL")
        assert resp.status_code == 502
        data = resp.json()
        assert "Upstream error" in data["detail"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_quote_endpoint_with_fake_client():
    """Integration test: verify quote endpoint works with fake client."""
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/quote/AAPL")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify quote response structure
        assert data["symbol"] == "AAPL"
        assert data["current_price"] == 123.45
        assert data["previous_close"] == 122.00
        assert data["open_price"] == 123.00
        assert data["high"] == 124.00
        assert data["low"] == 121.50
        assert data["volume"] == 1_000_000

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_info_endpoint_with_fake_client():
    """Integration test: verify info endpoint works with fake client."""
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/info/AAPL")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify info response structure
        assert data["symbol"] == "AAPL"
        assert data["short_name"] == "Fake Company Inc."
        assert data["currency"] == "USD"
        assert data["exchange"] == "NASDAQ"
        assert data["market_cap"] == 123_456_789_000

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_historical_endpoint_with_fake_client():
    """Integration test: verify historical endpoint works with fake client."""
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/historical/AAPL?interval=1d")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify historical response structure
        assert "symbol" in data
        assert "prices" in data
        assert len(data["prices"]) == 3  # FakeClient returns 3 days

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_earnings_endpoint_with_fake_client():
    """Integration test: verify earnings endpoint works with fake client."""
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/earnings/AAPL?frequency=quarterly")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Verify earnings response structure
        assert "symbol" in data
        assert "frequency" in data
        assert "rows" in data
        assert len(data["rows"]) == 4  # FakeClient returns 4 quarterly entries

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fake_client_implements_interface():
    """Unit test: verify FakeYFinanceClient properly implements the interface."""
    from app.clients.interface import YFinanceClientInterface

    client = FakeYFinanceClient()

    # Verify it's an instance of the interface
    assert isinstance(client, YFinanceClientInterface)

    # Test all interface methods exist and are callable
    assert callable(client.get_info)
    assert callable(client.get_history)
    assert callable(client.get_earnings)
    assert callable(client.get_income_statement)
    assert callable(client.get_calendar)
    assert callable(client.ping)

    # Test basic functionality
    info = await client.get_info("AAPL")
    assert info is not None
    assert info["symbol"] == "AAPL"

    history = await client.get_history("AAPL", start=None, end=None)
    assert history is not None
    assert not history.empty

    earnings = await client.get_earnings("AAPL")
    assert earnings is not None

    calendar = await client.get_calendar("AAPL")
    assert calendar is not None

    ping = await client.ping()
    assert ping is True
