"""Integration tests for API key authentication."""

import httpx
import pytest
from fastapi import Depends, FastAPI

from app.auth import check_api_key
from app.dependencies import get_settings, get_yfinance_client
from app.features.earnings.router import router as earnings_router
from app.features.health.router import router as health_router
from app.features.historical.router import router as historical_router
from app.features.info.router import router as info_router
from app.features.quote.router import router as quote_router
from app.features.snapshot.router import router as snapshot_router
from app.main import app
from app.settings import Settings
from tests.unit.clients.fake_client import FakeYFinanceClient


@pytest.fixture
def auth_app() -> FastAPI:
    """Create a FastAPI app with check_api_key as a global dependency.

    FastAPI adds global dependencies at initialization, so we cannot add ``check_api_key`` after it
    has been built.  Instead, tests that need authentication create a dedicated application where
    the dependency is wired from the start.
    """
    auth_app = FastAPI(dependencies=[Depends(check_api_key)])
    auth_app.include_router(quote_router, prefix="/quote", tags=["quote"])
    auth_app.include_router(historical_router, prefix="/historical", tags=["historical"])
    auth_app.include_router(info_router, prefix="/info", tags=["info"])
    auth_app.include_router(snapshot_router, prefix="/snapshot", tags=["snapshot"])
    auth_app.include_router(earnings_router, prefix="/earnings", tags=["earnings"])
    auth_app.include_router(health_router, tags=["health"])
    return auth_app


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset app state before and after each test."""
    app.dependency_overrides.clear()
    get_settings.cache_clear()

    yield

    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_key_disabled_allows_all_requests():
    """When API key auth is disabled, all requests should succeed without a key."""
    test_settings = Settings(api_key_enabled=False)

    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    app.dependency_overrides[get_settings] = lambda: test_settings

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/quote/AAPL")
        assert resp.status_code == 200

        resp = await client.get("/info/AAPL")
        assert resp.status_code == 200

        resp = await client.get("/snapshot/AAPL")
        assert resp.status_code == 200

        resp = await client.get("/historical/AAPL?interval=1d")
        assert resp.status_code == 200

        resp = await client.get("/earnings/AAPL?frequency=quarterly")
        assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_key_enabled_with_valid_key(auth_app: FastAPI):
    """When API key auth is enabled, requests with valid key should succeed."""
    test_settings = Settings(api_key="valid-test-key")

    auth_app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    auth_app.dependency_overrides[get_settings] = lambda: test_settings

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-API-Key": "valid-test-key"}

        resp = await client.get("/quote/AAPL", headers=headers)
        assert resp.status_code == 200

        resp = await client.get("/info/AAPL", headers=headers)
        assert resp.status_code == 200

        resp = await client.get("/snapshot/AAPL", headers=headers)
        assert resp.status_code == 200

        resp = await client.get("/historical/AAPL?interval=1d", headers=headers)
        assert resp.status_code == 200

        resp = await client.get("/earnings/AAPL?frequency=quarterly", headers=headers)
        assert resp.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_key_enabled_with_missing_key(auth_app: FastAPI):
    """When API key auth is enabled, requests without key should fail with 401."""
    test_settings = Settings(api_key="valid-test-key")

    auth_app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    auth_app.dependency_overrides[get_settings] = lambda: test_settings

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/quote/AAPL")
        assert resp.status_code == 401
        data = resp.json()
        assert "Missing API key" in data["detail"]

        resp = await client.get("/info/AAPL")
        assert resp.status_code == 401

        resp = await client.get("/snapshot/AAPL")
        assert resp.status_code == 401

        resp = await client.get("/historical/AAPL?interval=1d")
        assert resp.status_code == 401

        resp = await client.get("/earnings/AAPL?frequency=quarterly")
        assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_key_enabled_with_invalid_key(auth_app: FastAPI):
    """When API key auth is enabled, requests with invalid key should fail with 401."""
    test_settings = Settings(api_key="valid-test-key")

    auth_app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    auth_app.dependency_overrides[get_settings] = lambda: test_settings
    print(auth_app.router.dependencies)

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-API-Key": "invalid-key"}

        resp = await client.get("/quote/AAPL", headers=headers)
        assert resp.status_code == 401
        data = resp.json()
        assert "Invalid API key" in data["detail"]

        resp = await client.get("/info/AAPL", headers=headers)
        assert resp.status_code == 401

        resp = await client.get("/snapshot/AAPL", headers=headers)
        assert resp.status_code == 401

        resp = await client.get("/historical/AAPL?interval=1d", headers=headers)
        assert resp.status_code == 401

        resp = await client.get("/earnings/AAPL?frequency=quarterly", headers=headers)
        assert resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unprotected_endpoints(auth_app: FastAPI):
    """Test that unprotected endpoints work without API key."""
    test_settings = Settings(
        api_key="valid-test-key",
        api_key_unprotected_endpoints=["health", "quote"],
    )

    auth_app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    auth_app.dependency_overrides[get_settings] = lambda: test_settings

    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-API-Key": "invalid-key"}
        # Test that unprotected endpoints work without API key
        resp = await client.get("/health")
        assert resp.status_code == 200

        resp = await client.get("/quote/AAPL")
        assert resp.status_code == 200

        # Test other endpoints still require API key
        resp = await client.get("/info/AAPL", headers=headers)
        assert resp.status_code == 401

        resp = await client.get("/snapshot/AAPL", headers=headers)
        assert resp.status_code == 401

        resp = await client.get("/historical/AAPL?interval=1d", headers=headers)
        assert resp.status_code == 401

        resp = await client.get("/earnings/AAPL?frequency=quarterly", headers=headers)
        assert resp.status_code == 401
