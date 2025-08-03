import pytest

VALID_SYMBOL = "AAPL"
INVALID_SYMBOL = "!!!"


def test_quote_valid_symbol(client, mocker):
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_instance = mock_ticker.return_value
    mock_instance.info = {
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
    response = client.get(f"/quote/{INVALID_SYMBOL}")
    assert response.status_code == 400
    assert "Symbol must be" in response.json()["detail"]
