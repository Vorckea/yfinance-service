"""Tests for the /quote endpoint."""

from fastapi import HTTPException

VALID_SYMBOL = "AAPL"
INVALID_SYMBOL = "!!!"
NOT_FOUND_SYMBOL = "ZZZZZZZZZZ"


def test_quote_valid_symbol(client, mock_yfinance_client):
    """Test case for a valid symbol."""
    mock_yfinance_client.get_info.return_value = {
        "symbol": VALID_SYMBOL,
        "regularMarketPrice": 150.0,
        "regularMarketPreviousClose": 148.0,
        "regularMarketOpen": 149.0,
        "regularMarketDayHigh": 151.0,
        "regularMarketDayLow": 147.5,
        "regularMarketVolume": 1000000,
    }
    response = client.get(f"/quote/{VALID_SYMBOL}")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == VALID_SYMBOL
    assert data["current_price"] == 150.0


def test_quote_invalid_symbol(client):
    """Test case for an invalid symbol format."""
    response = client.get(f"/quote/{INVALID_SYMBOL}")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body and isinstance(body["detail"], list)


def test_quote_not_found_symbol(client, mock_yfinance_client):
    """Test case for a symbol not found."""
    mock_yfinance_client.get_info.side_effect = HTTPException(
        status_code=404, detail=f"No data for {NOT_FOUND_SYMBOL}"
    )
    response = client.get(f"/quote/{NOT_FOUND_SYMBOL}")
    assert response.status_code == 404
    assert "No data for" in response.json()["detail"]
