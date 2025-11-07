"""Tests for the bulk /quote endpoint.

Covers successful multi-symbol fetch and partial-failure behavior.
"""

import pytest
from fastapi import HTTPException

VALID_A = "AAPL"
VALID_B = "MSFT"
NOT_FOUND = "ZZZZZZ"


def test_quote_bulk_success(client, mock_yfinance_client):
    """Both symbols return valid data."""
    mapping = {
        VALID_A: {
            "symbol": VALID_A,
            "regularMarketPrice": 150.0,
            "regularMarketPreviousClose": 148.0,
            "regularMarketOpen": 149.0,
            "regularMarketDayHigh": 151.0,
            "regularMarketDayLow": 147.5,
            "regularMarketVolume": 1000000,
        },
        VALID_B: {
            "symbol": VALID_B,
            "regularMarketPrice": 300.0,
            "regularMarketPreviousClose": 298.0,
            "regularMarketOpen": 299.0,
            "regularMarketDayHigh": 301.0,
            "regularMarketDayLow": 297.5,
            "regularMarketVolume": 2000000,
        },
    }

    def _side(sym):
        return mapping[sym]

    mock_yfinance_client.get_info.side_effect = _side

    response = client.get(f"/quote?symbols={VALID_A},{VALID_B}")
    assert response.status_code == 200
    data = response.json()
    assert VALID_A in data and VALID_B in data
    assert data[VALID_A]["current_price"] == 150.0
    assert data[VALID_B]["current_price"] == 300.0


def test_quote_bulk_partial_failure(client, mock_yfinance_client):
    """One symbol succeeds, one returns HTTPException -> reported per-symbol."""

    def _side(sym):
        if sym == VALID_A:
            return {
                "symbol": VALID_A,
                "regularMarketPrice": 150.0,
                "regularMarketPreviousClose": 148.0,
                "regularMarketOpen": 149.0,
                "regularMarketDayHigh": 151.0,
                "regularMarketDayLow": 147.5,
            }
        raise HTTPException(status_code=404, detail=f"No data for {sym}")

    mock_yfinance_client.get_info.side_effect = _side

    response = client.get(f"/quote?symbols={VALID_A},{NOT_FOUND}")
    assert response.status_code == 200
    data = response.json()
    assert VALID_A in data and NOT_FOUND in data
    # success entry is a quote
    assert isinstance(data[VALID_A], dict)
    assert data[VALID_A]["current_price"] == 150.0
    # failure entry contains error and status_code
    assert isinstance(data[NOT_FOUND], dict)
    assert "error" in data[NOT_FOUND]
    assert data[NOT_FOUND]["status_code"] == 404