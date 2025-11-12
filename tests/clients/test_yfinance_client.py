import asyncio

import pandas as pd
import pytest
from fastapi import HTTPException

from app.clients.yfinance_client import YFinanceClient


@pytest.mark.asyncio
async def test_fetch_data_upstream_timeout(monkeypatch):
    """Simulate a TimeoutError -> should raise HTTP 503."""
    client = YFinanceClient()

    async def fake_to_thread(*args, **kwargs):
        raise asyncio.TimeoutError("Simulated timeout")

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    with pytest.raises(HTTPException) as excinfo:
        await client._fetch_data("info", lambda: None, "AAPL")

    assert excinfo.value.status_code == 503
    assert "timeout" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_fetch_data_cancelled_task(monkeypatch):
    """Simulate asyncio.CancelledError -> should raise HTTP 499."""
    client = YFinanceClient()

    async def fake_to_thread(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)

    with pytest.raises(HTTPException) as excinfo:
        await client._fetch_data("info", lambda: None, "AAPL")

    assert excinfo.value.status_code == 499
    assert "cancelled" in excinfo.value.detail.lower()


@pytest.mark.asyncio
async def test_get_info_non_dict(monkeypatch):
    """Simulate malformed info (non-dict) -> should raise HTTP 502."""
    client = YFinanceClient()
    ticker_mock = type("TickerMock", (), {"get_info": lambda self: ["invalid"]})()
    monkeypatch.setattr(client, "_get_ticker", lambda symbol: ticker_mock)

    async def mock_fetch_data(*a, **kw):
        return ["invalid"]

    monkeypatch.setattr(client, "_fetch_data", mock_fetch_data)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_info("AAPL")

    assert excinfo.value.status_code == 502


@pytest.mark.asyncio
async def test_get_info_empty(monkeypatch):
    """Simulate missing info (None or empty dict) -> should raise HTTP 404."""
    client = YFinanceClient()

    async def mock_fetch_data(*a, **kw):
        return None

    monkeypatch.setattr(client, "_fetch_data", mock_fetch_data)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_info("AAPL")

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_info_empty(monkeypatch):
    """Simulate missing info (None or empty dict) -> should raise HTTP 404."""
    client = YFinanceClient()

    async def mock_fetch_data(*a, **kw):
        return None

    monkeypatch.setattr(client, "_fetch_data", mock_fetch_data)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_info("AAPL")

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_history_empty_df(monkeypatch):
    """Simulate empty history -> should raise HTTP 404."""
    client = YFinanceClient()
    empty_df = pd.DataFrame()

    async def mock_fetch_data(*a, **kw):
        return empty_df

    monkeypatch.setattr(client, "_fetch_data", mock_fetch_data)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_history("AAPL", None, None)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_history_non_dataframe(monkeypatch):
    """Simulate malformed history (not a DataFrame) -> should raise HTTP 502."""
    client = YFinanceClient()

    async def mock_fetch_data(*a, **kw):
        return {"not": "df"}

    monkeypatch.setattr(client, "_fetch_data", mock_fetch_data)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_history("AAPL", None, None)

    assert excinfo.value.status_code == 502
