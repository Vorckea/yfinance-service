"""Tests for the /earnings endpoint."""

import pytest
import pandas as pd
import pytz

from app.features.earnings.service import fetch_earnings
from app.features.earnings.models import EarningsResponse
from fastapi import HTTPException
from unittest.mock import AsyncMock

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


def test_earnings_invalid_frequency(client):
    response = client.get(f"/earnings/{VALID_SYMBOL}?frequency=monthly")
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_fetch_earnings_info_failure():
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
    client.get_info.side_effect = HTTPException(status_code=503, detail="Info service unavailable")

    result = await fetch_earnings("AAPL", client, "quarterly")
    assert result.next_earnings_date is None  # Should gracefully handle missing info


@pytest.mark.asyncio
async def test_fetch_earnings_all_none_eps():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [None, None],
            "Estimated EPS": [1.8, 1.9],
            "Surprise": [None, None],
            "Surprise %": [None, None],
        },
        index=pd.DatetimeIndex(["2024-04-25", "2024-01-25"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")
    assert result.last_eps is None


@pytest.mark.asyncio
async def test_fetch_earnings_missing_column():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {"Estimated EPS": [1.8, 1.9]},  # "Reported EPS" missing
        index=pd.DatetimeIndex(["2024-04-25", "2024-01-25"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    with pytest.raises(KeyError):
        await fetch_earnings("AAPL", client, "quarterly")


@pytest.mark.asyncio
async def test_fetch_earnings_duplicate_dates():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.5, 2.0],
            "Estimated EPS": [1.4, 1.9],
            "Surprise": [0.1, 0.1],
            "Surprise %": [6.7, 5.3],
        },
        index=pd.DatetimeIndex(["2024-04-25", "2024-04-25"]),  # duplicate dates
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")
    assert len(result.rows) == 2
    assert result.last_eps == 1.5  # first non-None in sorted order


@pytest.mark.asyncio
async def test_fetch_earnings_future_date():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [2.0],
            "Estimated EPS": [1.95],
            "Surprise": [0.05],
            "Surprise %": [2.5],
        },
        index=pd.DatetimeIndex(["2025-01-01"]),  # future date
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")
    assert result.rows[0].earnings_date.strftime("%Y-%m-%d") == "2025-01-01"
    assert result.last_eps == 2.0


@pytest.mark.asyncio
async def test_fetch_earnings_unordered_dataframe():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.52, 1.95, 1.81],
            "Estimated EPS": [1.50, 1.89, 1.75],
            "Surprise": [0.02, 0.06, 0.06],
            "Surprise %": [1.33, 3.17, 3.43],
        },
        index=pd.DatetimeIndex(["2023-10-27", "2024-04-25", "2024-01-25"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")
    # Should sort and take most recent as last_eps
    assert result.last_eps == 1.95
    assert result.rows[0].earnings_date.strftime("%Y-%m-%d") == "2024-04-25"


@pytest.mark.asyncio
async def test_fetch_earnings_string_eps():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": ["1.95", "1.81"],
            "Estimated EPS": ["1.89", "1.75"],
            "Surprise": ["0.06", "0.06"],
            "Surprise %": ["3.17", "3.43"],
        },
        index=pd.DatetimeIndex(["2024-04-25", "2024-01-25"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")
    # Coerce string to float
    assert result.rows[0].reported_eps == 1.95

@pytest.mark.asyncio
async def test_fetch_earnings_nan_vs_none():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.95, None, float("nan")],
            "Estimated EPS": [1.89, 1.75, 1.80],
            "Surprise": [0.06, None, float("nan")],
            "Surprise %": [3.17, None, float("nan")],
        },
        index=pd.DatetimeIndex(["2024-04-25", "2024-01-25", "2023-10-27"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")
    # Should skip None/NaN when computing last_eps
    assert result.last_eps == 1.95
    assert result.rows[1].reported_eps is None
    assert result.rows[2].reported_eps is None


@pytest.mark.asyncio
async def test_fetch_earnings_with_timezone():
    client = AsyncMock()

    tz = pytz.timezone("US/Eastern")
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.95],
            "Estimated EPS": [1.89],
            "Surprise": [0.06],
            "Surprise %": [3.17],
        },
        index=pd.DatetimeIndex(["2024-04-25"]).tz_localize(tz),
    )

    client.get_earnings.return_value = earnings_df
    client.get_calendar = AsyncMock(
        return_value={"Earnings Date": ["2025-01-01"]}
    )
    client.get_info = AsyncMock(return_value={})

    result = await fetch_earnings("AAPL", client, "quarterly")
    row = result.rows[0]

    assert row.earnings_date is not None
    assert row.earnings_date.isoformat() == "2024-04-25"

    assert result.next_earnings_date is not None
    assert result.next_earnings_date.isoformat() == "2025-01-01"



@pytest.mark.asyncio
async def test_fetch_earnings_both_upstream_failures():
    client = AsyncMock()
    client.get_earnings.side_effect = HTTPException(status_code=503, detail="Earnings service unavailable")
    client.get_info.side_effect = HTTPException(status_code=503, detail="Info service unavailable")

    with pytest.raises(HTTPException) as exc:
        await fetch_earnings("AAPL", client, "quarterly")
    
    assert exc.value.status_code == 503
    assert "Earnings service unavailable" in exc.value.detail


@pytest.mark.asyncio
async def test_fetch_earnings_unusual_indices():
    client = AsyncMock()

    # Mixed timezones
    tz_est = pytz.timezone("US/Eastern")
    tz_utc = pytz.UTC

    dates = [
        pd.Timestamp("2024-01-25 10:00", tz=pytz.UTC),
        pd.Timestamp("2024-04-25 15:00", tz=pytz.UTC),
        pd.Timestamp("2024-01-30 12:00", tz=pytz.UTC),
    ]

    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [1.8, 2.0, 1.9],
            "Estimated EPS": [1.75, 1.95, 1.85],
            "Surprise": [0.05, 0.05, 0.05],
            "Surprise %": [2.7, 2.6, 2.8],
        },
        index=pd.DatetimeIndex(dates)
    )

    client.get_earnings.return_value = earnings_df
    client.get_info.return_value = {}

    result = await fetch_earnings("AAPL", client, "quarterly")

    # Ensure sorting by datetime worked and last_eps is correct
    assert result.last_eps == 2.0
    assert len(result.rows) == 3


@pytest.mark.asyncio
async def test_fetch_earnings_corrupt_data_types():
    client = AsyncMock()
    earnings_df = pd.DataFrame(
        {
            "Reported EPS": [[1.95], "abc", 1.81],  # invalid types
            "Estimated EPS": [1.89, 1.75, 1.50],
            "Surprise": [0.06, 0.06, 0.02],
            "Surprise %": [3.17, 3.43, 1.33],
        },
        index=pd.DatetimeIndex(["2024-04-25", "2024-01-25", "2023-10-27"]),
    )
    client.get_earnings.return_value = earnings_df
    client.get_calendar.return_value = {}

    # After fix: should NOT raise - returns gracefully with corrupt data handling
    result = await fetch_earnings("AAPL", client, "quarterly")
    assert result is not None
    # Should have entries but with None values for corrupt EPS
    assert len(result.rows) > 0

@pytest.mark.integration
@pytest.mark.skip(reason="requires real upstream API")
def test_earnings_integration_real_service():
    import requests

    symbol = "AAPL"
    response = requests.get(f"https://api.example.com/earnings/{symbol}?frequency=quarterly")
    assert response.status_code == 200
    data = response.json()
    assert "rows" in data
    assert len(data["rows"]) > 0
    assert data["last_eps"] is not None

