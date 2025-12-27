"""Tests for the /health endpoint."""


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
