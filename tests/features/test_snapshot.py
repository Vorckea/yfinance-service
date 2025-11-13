"""Tests for the /snapshot endpoint."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.features.snapshot.models import SnapshotResponse
from app.features.snapshot.service import fetch_snapshot

VALID_SYMBOL = "AAPL"
INVALID_SYMBOL = "!!!"

# Tests for the HTTP endpoint (GET /snapshot/{symbol})
def test_snapshot_valid_symbol_success(client, mock_yfinance_client):
    """Test successful snapshot fetch for a valid symbol."""
    # Setup: mock info and quote data
    mock_yfinance_client.get_info.return_value = {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "website": "https://www.apple.com",
        "longBusinessSummary": "Apple Inc. designs consumer electronics.",
        "marketCap": 2500000000000,
        "sharesOutstanding": 16000000000,
        "dividendYield": 0.006,
        "fiftyTwoWeekHigh": 175.0,
        "fiftyTwoWeekLow": 120.0,
        "currentPrice": 150.0,
        "trailingPE": 28.0,
        "beta": 1.2,
        "address1": "1 Apple Park Way, Cupertino, CA 95014, USA",
        "currency": "USD",
        # Include quote fields for quote mapping
        "regularMarketPrice": 150.0,
        "regularMarketPreviousClose": 148.0,
        "regularMarketOpen": 149.0,
        "regularMarketDayHigh": 151.0,
        "regularMarketDayLow": 147.5,
        "regularMarketVolume": 1000000,
    }

    response = client.get(f"/snapshot/{VALID_SYMBOL}")
    assert response.status_code == 200
    data = response.json()

    # Verify sequence: symbol, info, quote
    assert "symbol" in data
    assert "info" in data
    assert "quote" in data
    assert data["symbol"] == VALID_SYMBOL

    # Verify info fields
    info = data["info"]
    assert info["symbol"] == VALID_SYMBOL
    assert info["short_name"] == "Apple Inc."
    assert info["exchange"] == "NASDAQ"
    assert info["sector"] == "Technology"

    # Verify quote fields
    quote = data["quote"]
    assert quote["symbol"] == VALID_SYMBOL
    assert quote["current_price"] == 150.0
    assert quote["previous_close"] == 148.0
    assert quote["open_price"] == 149.0
    assert quote["volume"] == 1000000


def test_snapshot_invalid_symbol(client):
    """Test snapshot endpoint with invalid symbol format."""
    response = client.get(f"/snapshot/{INVALID_SYMBOL}")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body and isinstance(body["detail"], list)


def test_snapshot_info_fetch_fails_returns_502(client, mock_yfinance_client):
    """Test that snapshot returns 502 if info fetch fails."""
    # First call (fetch_info) fails; second call would be fetch_quote but we should not reach it
    mock_yfinance_client.get_info.side_effect = HTTPException(
        status_code=502, detail="Upstream data unavailable"
    )

    response = client.get(f"/snapshot/{VALID_SYMBOL}")
    assert response.status_code == 502
    assert "Upstream" in response.json()["detail"]


def test_snapshot_quote_fetch_fails_returns_502(client, mock_yfinance_client):
    """Test that snapshot returns 502 if quote fetch fails (validation error)."""
    # Mock returns incomplete quote data; quote parsing will fail
    mock_yfinance_client.get_info.return_value = {
        # Info fields (sufficient for info fetch)
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "exchange": "NASDAQ",
        # Missing quote required fields
        "regularMarketPrice": 150.0,
        # Missing other required quote fields: previous_close, open, high, low
    }

    response = client.get(f"/snapshot/{VALID_SYMBOL}")
    assert response.status_code == 502
    assert "Missing required fields" in response.json()["detail"] or "Malformed" in response.json()[
        "detail"
    ]

# Tests for the service function (fetch_snapshot)
@pytest.mark.asyncio
async def test_fetch_snapshot_success():
    """Test successful snapshot fetch with valid info and quote data."""
    client_mock = AsyncMock()
    client_mock.get_info.return_value = {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "website": "https://www.apple.com",
        "longBusinessSummary": "Apple Inc. designs consumer electronics.",
        "marketCap": 2500000000000,
        "sharesOutstanding": 16000000000,
        "dividendYield": 0.006,
        "fiftyTwoWeekHigh": 175.0,
        "fiftyTwoWeekLow": 120.0,
        "currentPrice": 150.0,
        "trailingPE": 28.0,
        "beta": 1.2,
        "address1": "1 Apple Park Way, Cupertino, CA 95014, USA",
        "currency": "USD",
        "regularMarketPrice": 150.0,
        "regularMarketPreviousClose": 148.0,
        "regularMarketOpen": 149.0,
        "regularMarketDayHigh": 151.0,
        "regularMarketDayLow": 147.5,
        "regularMarketVolume": 1000000,
    }

    result = await fetch_snapshot(VALID_SYMBOL, client_mock)

    assert isinstance(result, SnapshotResponse)
    assert result.symbol == VALID_SYMBOL
    assert result.info.symbol == VALID_SYMBOL
    assert result.quote.symbol == VALID_SYMBOL
    assert result.quote.current_price == 150.0
    assert result.info.short_name == "Apple Inc."


@pytest.mark.asyncio
async def test_fetch_snapshot_info_fetch_fails():
    """Test that fetch_snapshot raises 502 if fetch_info fails."""
    client_mock = AsyncMock()
    # Simulate info fetch failure (could be called first during execution)
    client_mock.get_info.side_effect = HTTPException(status_code=502, detail="Info unavailable")

    with pytest.raises(HTTPException) as exc:
        await fetch_snapshot(VALID_SYMBOL, client_mock)

    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_fetch_snapshot_quote_validation_fails():
    """Test that fetch_snapshot raises 502 if quote validation fails (missing fields)."""
    client_mock = AsyncMock()
    # Return data with missing quote required fields
    client_mock.get_info.return_value = {
        # Info fields
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        # Quote fields - missing required ones
        "regularMarketPrice": 150.0,
    }

    with pytest.raises(HTTPException) as exc:
        await fetch_snapshot(VALID_SYMBOL, client_mock)

    assert exc.value.status_code == 502
    assert "Missing required fields" in exc.value.detail or "Malformed" in exc.value.detail


@pytest.mark.asyncio
async def test_fetch_snapshot_quote_malformed_data():
    """Test that fetch_snapshot raises 502 if quote data is malformed."""
    client_mock = AsyncMock()
    client_mock.get_info.return_value = {
        # Info fields
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        # Quote fields with malformed data
        "regularMarketPrice": "not-a-number",  # Invalid
        "regularMarketPreviousClose": 148.0,
        "regularMarketOpen": 149.0,
        "regularMarketDayHigh": 151.0,
        "regularMarketDayLow": 147.5,
    }

    with pytest.raises(HTTPException) as exc:
        await fetch_snapshot(VALID_SYMBOL, client_mock)

    assert exc.value.status_code == 502
    assert "Malformed" in exc.value.detail


@pytest.mark.asyncio
async def test_fetch_snapshot_normalizes_symbol():
    """Test that fetch_snapshot normalizes the symbol (uppercase, strip)."""
    client_mock = AsyncMock()
    client_mock.get_info.return_value = {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "exchange": "NASDAQ",
        "regularMarketPrice": 150.0,
        "regularMarketPreviousClose": 148.0,
        "regularMarketOpen": 149.0,
        "regularMarketDayHigh": 151.0,
        "regularMarketDayLow": 147.5,
    }

    result = await fetch_snapshot("  aapl  ", client_mock)

    assert result.symbol == "AAPL"
    assert result.info.symbol == "AAPL"
    assert result.quote.symbol == "AAPL"


@pytest.mark.asyncio
async def test_fetch_snapshot_with_no_volume():
    """Test that snapshot succeeds even when volume is missing."""
    client_mock = AsyncMock()
    client_mock.get_info.return_value = {
        # Info fields
        "shortName": "Apple Inc.",
        # Quote fields without volume
        "regularMarketPrice": 150.0,
        "regularMarketPreviousClose": 148.0,
        "regularMarketOpen": 149.0,
        "regularMarketDayHigh": 151.0,
        "regularMarketDayLow": 147.5,
        # regularMarketVolume missing
    }

    result = await fetch_snapshot(VALID_SYMBOL, client_mock)

    assert isinstance(result, SnapshotResponse)
    assert result.quote.volume is None
