"""Tests for the /earnings endpoint."""

import pytest
import pandas as pd
from datetime import date
from fastapi import HTTPException

from app.features.earnings.service import fetch_earnings
from app.features.earnings.models import EarningsResponse


VALID_SYMBOL = "AAPL"
INVALID_SYMBOL = "!!!"
NOT_FOUND_SYMBOL = "ZZZZZZZZZZ"


def test_earnings_valid_symbol_quarterly(client, mock_yfinance_client):
    """Test case for a valid symbol with quarterly earnings."""
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.95, 1.81, 1.52],
            "Estimated EPS": [1.89, 1.75, 1.50],
            "Surprise": [0.06, 0.06, 0.02],
            "Surprise %": [3.17, 3.43, 1.33],
        },
        index=pd.DatetimeIndex(["2024-04-25", "2024-01-25", "2023-10-27"]),
    )

    mock_yfinance_client.get_info.return_value = {"nextEarningsDate": 1717200000}  # 2024-06-01
    mock_yfinance_client.get_earnings.return_value = earnings_df

    response = client.get(f"/earnings/{VALID_SYMBOL}?frequency=quarterly")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == VALID_SYMBOL
    assert data["frequency"] == "quarterly"
    assert len(data["rows"]) == 3
    assert data["rows"][0]["earnings_date"] == "2024-04-25"  # most recent first
    assert data["rows"][0]["reported_eps"] == 1.95
    assert data["last_eps"] == 1.95
    assert data["next_earnings_date"] == "2024-06-01"


def test_earnings_valid_symbol_annual(client, mock_yfinance_client):
    """Test case for annual earnings."""
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [7.94, 6.05],
            "Estimated EPS": [7.80, 5.95],
            "Surprise": [0.14, 0.10],
            "Surprise %": [1.79, 1.68],
        },
        index=pd.DatetimeIndex(["2024-01-30", "2023-01-31"]),
    )

    mock_yfinance_client.get_info.return_value = {}
    mock_yfinance_client.get_earnings.return_value = earnings_df

    response = client.get(f"/earnings/{VALID_SYMBOL}?frequency=annual")
    assert response.status_code == 200
    data = response.json()
    assert data["frequency"] == "annual"
    assert len(data["rows"]) == 2
    assert data["last_eps"] == 7.94


def test_earnings_invalid_symbol(client):
    """Test case for an invalid symbol format."""
    response = client.get(f"/earnings/{INVALID_SYMBOL}")
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body


def test_earnings_not_found_symbol(client, mock_yfinance_client):
    """Test case for a symbol with no earnings data."""
    mock_yfinance_client.get_earnings.side_effect = HTTPException(
        status_code=404, detail=f"No quarterly earnings data for {NOT_FOUND_SYMBOL}"
    )

    response = client.get(f"/earnings/{NOT_FOUND_SYMBOL}")
    assert response.status_code == 404
    assert "No quarterly earnings data" in response.json()["detail"]


def test_earnings_upstream_timeout(client, mock_yfinance_client):
    """Test case for upstream timeout."""
    mock_yfinance_client.get_earnings.side_effect = HTTPException(
        status_code=503, detail="Upstream timeout"
    )

    response = client.get(f"/earnings/{VALID_SYMBOL}")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_fetch_earnings_empty_dataframe():
    """Empty earnings DataFrame should raise 404."""
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.get_earnings.return_value = pd.DataFrame()

    with pytest.raises(HTTPException) as exc:
        await fetch_earnings("AAPL", client, "quarterly")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_earnings_with_missing_values():
    """Earnings with some missing fields should still map correctly."""
    from unittest.mock import AsyncMock

    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.95, None],
            "Estimated EPS": [1.89, 1.75],
            "Surprise": [0.06, None],
            "Surprise %": [3.17, None],
        },
        index=pd.DatetimeIndex(["2024-04-25", "2024-01-25"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")
    assert isinstance(result, EarningsResponse)
    assert len(result.rows) == 2
    assert result.rows[0].reported_eps == 1.95
    assert result.rows[1].reported_eps is None
    assert result.last_eps == 1.95  # first non-None


@pytest.mark.asyncio
async def test_fetch_earnings_no_next_earnings_date():
    """Earnings fetch should handle missing next_earnings_date gracefully."""
    from unittest.mock import AsyncMock

    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.95],
            "Estimated EPS": [1.89],
            "Surprise": [0.06],
            "Surprise %": [3.17],
        },
        index=pd.DatetimeIndex(["2024-04-25"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}  # No nextEarningsDate

    result = await fetch_earnings("AAPL", client, "quarterly")
    assert result.next_earnings_date is None
