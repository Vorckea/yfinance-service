"""Global test fixtures and configurations for the FastAPI application."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_yfinance_client
from app.main import app


@pytest.fixture(scope="function")
def mock_yfinance_client(mocker):
    """Fixture to mock the YFinanceClient, providing async-compatible mocks."""
    mock = mocker.patch("app.dependencies.get_yfinance_client", autospec=True)
    client_instance = mock.return_value
    client_instance.get_info = AsyncMock()
    client_instance.get_history = AsyncMock()
    client_instance.ping = AsyncMock()
    return client_instance


@pytest.fixture(scope="function")
def client(mock_yfinance_client):
    """Test client fixture that injects the mocked YFinanceClient."""
    app.dependency_overrides[get_yfinance_client] = lambda: mock_yfinance_client
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
