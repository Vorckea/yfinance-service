"""Global test fixtures and configurations for the FastAPI application."""


import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import app
from app.dependencies import get_yfinance_client, get_info_cache
from app.utils.cache import SnapshotCache

from tests.clients.fake_client import FakeYFinanceClient


@pytest.fixture(scope="function")
def mock_yfinance_client(mocker):
    """Fixture to mock the YFinanceClient, providing async-compatible mocks."""
    mock = mocker.patch("app.dependencies.get_yfinance_client", autospec=True)
    client_instance = mock.return_value
    client_instance.get_info = AsyncMock()
    client_instance.get_history = AsyncMock()
    client_instance.get_earnings = AsyncMock()
    client_instance.ping = AsyncMock()
    return client_instance


@pytest.fixture(scope="function")
def client(mock_yfinance_client):
    """Test client fixture that injects the mocked YFinanceClient."""
    from app.dependencies import get_earnings_cache
    
    app.dependency_overrides[get_yfinance_client] = lambda: mock_yfinance_client
    # Also override cache for snapshot tests
    app.dependency_overrides[get_info_cache] = lambda: SnapshotCache(maxsize=32, ttl=300)
    # Override earnings cache to ensure fresh cache for each test (lru_cache returns same instance)
    app.dependency_overrides[get_earnings_cache] = lambda: SnapshotCache(maxsize=128, ttl=3600)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def fake_yfinance_client():
    """Provide a deterministic fake YFinance client for tests."""
    return FakeYFinanceClient()


@pytest.fixture(scope="function")
def client_fake(fake_yfinance_client):
    """FastAPI test client using the fake YFinance client instead of mock."""
    from app.dependencies import get_earnings_cache
    
    app.dependency_overrides[get_yfinance_client] = lambda: fake_yfinance_client
    app.dependency_overrides[get_info_cache] = lambda: SnapshotCache(maxsize=32, ttl=300)
    app.dependency_overrides[get_earnings_cache] = lambda: SnapshotCache(maxsize=128, ttl=3600)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# Pytest configuration to register custom markers
def pytest_configure(config):
    """Register a custom marker for tests using the fake client."""
    config.addinivalue_line(
        "markers", "usefakeclient: use the deterministic fake YFinance client instead of mocks"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Auto-switch to fake client when test is marked with @pytest.mark.usefakeclient."""
    if "usefakeclient" in item.keywords:
        # Override FastAPI dependency before the test runs
        from app.dependencies import get_yfinance_client, get_info_cache
        from tests.clients.fake_client import FakeYFinanceClient
        from app.main import app

        app.dependency_overrides[get_yfinance_client] = lambda: FakeYFinanceClient()
        app.dependency_overrides[get_info_cache] = lambda: SnapshotCache(maxsize=32, ttl=300)

