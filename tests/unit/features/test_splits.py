"""Tests for the /splits endpoint."""

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

VALID_SYMBOL = "AAPL"
INVALID_SYMBOL = "!!!"
NOT_FOUND_SYMBOL = "ZZZZZZZZZZ"

def test_read_splits_valid_symbol(client, mock_yfinance_client):
    """Test successful splits fetch for a valid symbol using mocked data."""
    # Create fake data for splits
    mock_data = pd.Series(
        data=[2.0, 7.0], 
        index=pd.to_datetime(["1987-06-16", "2014-06-09"])
    )
    
    # Patching 'yfinance' to prevent the test from hitting the real Yahoo Finance API.
    with patch("app.features.splits.service.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.splits = mock_data

        response = client.get(f"/splits/{VALID_SYMBOL}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["ratio"] == 2.0
        assert "1987-06-16" in data[0]["date"]

def test_read_splits_invalid_symbol(client):
    """Test splits endpoint with invalid symbol format (Pydantic validation)."""
    # This triggers the 422 error because of the project's internal validators
    response = client.get(f"/splits/{INVALID_SYMBOL}")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body and isinstance(body["detail"], list)

def test_read_splits_not_found_symbol(client, mock_yfinance_client):
    """Test case for a symbol that returns no split data."""
    with patch("app.features.splits.service.yf.Ticker") as mock_ticker:
        # Simulate an empty series returned for a ticker that has no splits
        mock_ticker.return_value.splits = pd.Series(dtype=float)
        
        response = client.get(f"/splits/{NOT_FOUND_SYMBOL}")
        
        assert response.status_code == 200
        assert response.json() == []

@pytest.mark.asyncio
async def test_fetch_splits_empty_upstream_logic():
    """Test service logic directly when upstream returns an empty series."""
    with patch("app.features.splits.service.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.splits = pd.Series(dtype=float)
        
        from app.features.splits.service import get_splits
        
        result = get_splits(VALID_SYMBOL)
        assert result == []