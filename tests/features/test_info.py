VALID_SYMBOL = "AAPL"
INVALID_SYMBOL = "!!!"
NOT_FOUND_SYMBOL = "ZZZZZZZZZZ"  # unlikely to exist


def test_info_valid_symbol(client, mocker):
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_instance = mock_ticker.return_value
    mock_instance.info = {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "website": "https://www.apple.com",
        "longBusinessSummary": "Apple Inc. designs, manufactures, and markets consumer electronics, software, and services.",
        "marketCap": 2500000000000,
        "sharesOutstanding": 16000000000,
        "dividendYield": 0.006,
        "fiftyTwoWeekHigh": 175.0,
        "fiftyTwoWeekLow": 120.0,
        "currentPrice": 150.0,
        "trailingPE": 28.0,
        "beta": 1.2,
        "address1": "1 Apple Park Way, Cupertino, CA 95014, USA",
    }
    response = client.get(f"/info/{VALID_SYMBOL}")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == VALID_SYMBOL
    assert data["short_name"] == "Apple Inc."
    assert data["current_price"] == 150.0
    assert data["address"] == "1 Apple Park Way, Cupertino, CA 95014, USA"


def test_info_invalid_symbol(client):
    response = client.get(f"/info/{INVALID_SYMBOL}")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body and isinstance(body["detail"], list)


def test_info_not_found_symbol(client, mocker):
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_instance = mock_ticker.return_value
    mock_instance.info = {}
    response = client.get(f"/info/{NOT_FOUND_SYMBOL}")
    assert response.status_code == 404
    assert "No data for" in response.json()["detail"]
