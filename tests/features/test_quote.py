"""Tests for the /quote endpoint."""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.features.quote.service import QuoteResponse, fetch_quote

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


@pytest.mark.asyncio
async def test_fetch_quote_upstream_none():
    """Upstream returns None -> should raise 502."""
    client = AsyncMock()
    client.get_info.return_value = None
    with pytest.raises(HTTPException) as exc:
        await fetch_quote("AAPL", client)
    assert exc.value.status_code == 502
    assert "No data from upstream" in exc.value.detail


@pytest.mark.asyncio
async def test_fetch_quote_upstream_empty():
    """Upstream returns empty dict -> should raise 502."""
    client = AsyncMock()
    client.get_info.return_value = {}
    with pytest.raises(HTTPException) as exc:
        await fetch_quote("AAPL", client)
    assert exc.value.status_code == 502
    assert "No data from upstream" in exc.value.detail


@pytest.mark.asyncio
async def test_fetch_quote_missing_required_fields():
    """Upstream missing a required field -> should raise 502 with symbol."""
    client = AsyncMock()
    client.get_info.return_value = {"regularMarketPrice": 100.0}  # missing others
    with pytest.raises(HTTPException) as exc:
        await fetch_quote("AAPL", client)
    assert exc.value.status_code == 502
    assert "Malformed quote data" in exc.value.detail
    assert "AAPL" in exc.value.detail


@pytest.mark.asyncio
async def test_fetch_quote_malformed_numbers():
    """Upstream has malformed numeric fields -> should raise 502."""
    client = AsyncMock()
    client.get_info.return_value = {
        "regularMarketPrice": "not-a-number",  # invalid
        "regularMarketPreviousClose": 95.0,
        "regularMarketOpen": 98.0,
        "regularMarketDayHigh": 102.0,
        "regularMarketDayLow": 94.0,
    }
    with pytest.raises(HTTPException) as exc:
        await fetch_quote("AAPL", client)
    assert exc.value.status_code == 502
    assert "Malformed quote data" in exc.value.detail


@pytest.mark.asyncio
async def test_fetch_quote_missing_volume():
    """Upstream missing optional volume -> should succeed, volume None."""
    client = AsyncMock()
    client.get_info.return_value = {
        "regularMarketPrice": 100.0,
        "regularMarketPreviousClose": 95.0,
        "regularMarketOpen": 98.0,
        "regularMarketDayHigh": 102.0,
        "regularMarketDayLow": 94.0,
        # volume missing
    }
    result = await fetch_quote("AAPL", client)
    assert isinstance(result, QuoteResponse)
    assert result.volume is None
