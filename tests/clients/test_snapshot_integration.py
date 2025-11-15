import pytest
import httpx
from unittest.mock import AsyncMock
from app.main import app
from app.dependencies import get_yfinance_client, get_info_cache
from tests.clients.fake_client import FakeYFinanceClient
from app.utils.cache import SnapshotCache


@pytest.mark.asyncio
@pytest.mark.integration
async def test_snapshot_staging():
    """Integration test using FakeYFinanceClient (deterministic)."""
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/snapshot/AAPL")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert "current_price" in data
        assert "currency" in data
        assert data["current_price"] == 123.45
        assert data["currency"] == "USD"
        assert "info" in data
        assert "quote" in data

    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_snapshot_info_caching():
    """Integration test: verify quote is fetched fresh on each request (via get_snapshot calls)."""
    call_counts = {"get_snapshot_called": 0}
    
    class CountingFakeClient(FakeYFinanceClient):
        async def get_snapshot(self, symbol: str):
            call_counts["get_snapshot_called"] += 1
            return await super().get_snapshot(symbol)

    counting_client = CountingFakeClient()
    # Use a shared cache instance for this test
    info_cache = SnapshotCache(maxsize=32, ttl=60)

    app.dependency_overrides[get_yfinance_client] = lambda: counting_client
    app.dependency_overrides[get_info_cache] = lambda: info_cache

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First request: fetch snapshot
        resp1 = await client.get("/snapshot/AAPL")
        assert resp1.status_code == 200
        get_snapshot_calls_first = call_counts["get_snapshot_called"]
        assert get_snapshot_calls_first >= 1, "Expected at least one snapshot call"

        # Second request: quote should be fresh (snapshot called again)
        resp2 = await client.get("/snapshot/AAPL")
        assert resp2.status_code == 200
        
        # Snapshot/quote should have been called again (always fresh)
        assert call_counts["get_snapshot_called"] > get_snapshot_calls_first, (
            f"Expected get_snapshot to be called fresh on second request, "
            f"but total calls: {call_counts['get_snapshot_called']}, after first: {get_snapshot_calls_first}"
        )

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

