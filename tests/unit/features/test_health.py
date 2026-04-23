"""Tests for the /health endpoint."""

import time
import pytest
from app.features.health.router import ready_cache

@pytest.fixture(autouse=True)
async def clear_ready_cache():
    await ready_cache.clear()

def test_health_check_ok(client, mock_yfinance_client):
    """Test case for a successful health check."""
    mock_yfinance_client.ping.return_value = True
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_failed(client, mock_yfinance_client):
    """Test case for a failed health check."""
    mock_yfinance_client.ping.return_value = False
    response = client.get("/ready")
    assert response.status_code == 503
    assert "Not ready" in response.json()["detail"]
def test_ready_cache_hit(client, mock_yfinance_client):
    """Second call should use cache (no extra ping)."""

    mock_yfinance_client.ping.return_value = True

    # First call → MISS
    response1 = client.get("/ready")
    assert response1.status_code == 200

    # Second call → should be cached
    response2 = client.get("/ready")
    assert response2.status_code == 200

    # ping should be called ONLY once due to cache
    assert mock_yfinance_client.ping.call_count == 1

def test_ready_cache_miss(client, mock_yfinance_client):
    """First call should hit actual client (cache miss)."""

    mock_yfinance_client.ping.return_value = True

    response = client.get("/ready")

    assert response.status_code == 200
    assert mock_yfinance_client.ping.call_count == 1
    


def test_ready_cache_expiry(client, mock_yfinance_client):
    """Cache should expire after TTL."""

    mock_yfinance_client.ping.return_value = True

    # First call
    client.get("/ready")

    # Wait for TTL expiry (adjust based on your TTL)
    time.sleep(3)

    # Second call → should call ping again
    client.get("/ready")

    assert mock_yfinance_client.ping.call_count == 2