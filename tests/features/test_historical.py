"""Tests for the /historical endpoint."""

import pandas as pd
from fastapi import HTTPException

VALID_SYMBOLS = "AAPL"
INVALID_SYMBOLS = "!!!"
NOT_FOUND_SYMBOL = "ZZZZZZZZZZ"


def test_historical_valid_symbol(client, mock_yfinance_client):
    """Test case for a valid symbol."""
    mock_yfinance_client.get_history.return_value = pd.DataFrame(
        {
            "Open": [150.0, 151.0],
            "High": [152.0, 153.0],
            "Low": [149.0, 150.0],
            "Close": [151.0, 152.0],
            "Volume": [1000000, 1100000],
        },
        index=pd.to_datetime(["2024-08-01", "2024-08-02"]),
    )
    response = client.get(f"/historical/{VALID_SYMBOLS}?start=2024-08-01&end=2024-08-02")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == VALID_SYMBOLS.upper()
    assert len(data["prices"]) == 2
    assert data["prices"][0]["date"] == "2024-08-01"
    assert data["prices"][0]["open"] == 150.0
    assert data["prices"][0]["high"] == 152.0
    assert data["prices"][0]["low"] == 149.0
    assert data["prices"][0]["close"] == 151.0
    assert data["prices"][0]["volume"] == 1000000


def test_historical_invalid_symbol(client):
    """Test case for an invalid symbol format."""
    response = client.get(f"/historical/{INVALID_SYMBOLS}?start=2024-08-01&end=2024-08-02")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body and isinstance(body["detail"], list)


def test_historical_not_found(client, mock_yfinance_client):
    """Test case for a symbol not found."""
    mock_yfinance_client.get_history.side_effect = HTTPException(
        status_code=404, detail=f"No data for {NOT_FOUND_SYMBOL}"
    )
    response = client.get(f"/historical/{NOT_FOUND_SYMBOL}")
    assert response.status_code == 404
    assert "No data for" in response.json()["detail"]
