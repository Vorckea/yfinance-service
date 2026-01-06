"""Integration tests for API key authentication."""

import httpx
import pytest

from app.dependencies import get_settings, get_yfinance_client
from app.main import app
from app.settings import Settings
from tests.unit.clients.fake_client import FakeYFinanceClient


@pytest.fixture(autouse=True)
def reset_app_state():
    """Reset app state before and after each test."""
    # Clear before test
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    
    yield
    
    # Clear after test
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_api_key_disabled_allows_all_requests():
    """When API key auth is disabled, all requests should succeed without a key."""
    # Create settings instance
    test_settings = Settings(
        api_key_enabled=False,
        api_key="test-key-123"
    )
    
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test various endpoints without API key
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
async def test_api_key_enabled_with_valid_key():
    """When API key auth is enabled, requests with valid key should succeed."""
    test_settings = Settings(
        api_key_enabled=True,
        api_key="valid-test-key"
    )
    
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-API-Key": "valid-test-key"}
        
        # Test various endpoints with valid API key
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
async def test_api_key_enabled_with_missing_key():
    """When API key auth is enabled, requests without key should fail with 401."""
    test_settings = Settings(
        api_key_enabled=True,
        api_key="valid-test-key"
    )
    
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test various endpoints without API key
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
async def test_api_key_enabled_with_invalid_key():
    """When API key auth is enabled, requests with invalid key should fail with 401."""
    test_settings = Settings(
        api_key_enabled=True,
        api_key="valid-test-key"
    )
    
    app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-API-Key": "invalid-key"}
        
        # Test various endpoints with invalid API key
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
async def test_health_endpoint_unprotected():
    """Health endpoint should work without API key even when auth is enabled."""
    test_settings = Settings(
        api_key_enabled=True,
        api_key="valid-test-key"
    )
    
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check should work without API key
        resp = await client.get("/health")
        assert resp.status_code == 200
        



