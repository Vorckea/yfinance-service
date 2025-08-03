import pandas as pd

VALID_SYMBOLS = "AAPL"
INVALID_SYMBOLS = "!!!"


def test_historical_valid_symbol(client, mocker):
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_instance = mock_ticker.return_value
    mock_instance.history.return_value = pd.DataFrame(
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
    response = client.get(f"/historical/{INVALID_SYMBOLS}?start=2024-08-01&end=2024-08-02")
    assert response.status_code == 400
    assert "Symbol must be" in response.json()["detail"]


def test_historical_not_found(client, mocker):
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_instance = mock_ticker.return_value
    # Return empty DataFrame to simulate no data
    mock_instance.history.return_value = pd.DataFrame()
    response = client.get("/historical/ZZZZZZZZZZ")
    assert response.status_code == 404
    assert "No historical data for symbol" in response.json()["detail"]
