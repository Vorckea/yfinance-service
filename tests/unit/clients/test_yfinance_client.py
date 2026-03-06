"""Tests for YFinanceClient error handling."""

import asyncio

import pandas as pd
import pytest
from fastapi import HTTPException

from app.clients.yfinance_client import YFinanceClient
from app.settings import Settings


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
async def test_fetch_data_retry_succeeds_on_second_attempt(monkeypatch):
    """Test that a transient error retries and eventually succeeds."""
    client = YFinanceClient()
    call_count = [0]
    
    async def fake_to_thread(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 2:
            # First call fails with TimeoutError
            raise asyncio.TimeoutError("Transient timeout")
        # Second call succeeds
        return {"data": "success"}
    
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    
    result = await client._fetch_data("info", lambda: None, "AAPL")
    
    assert result == {"data": "success"}
    assert call_count[0] == 2  # Should have been called twice


@pytest.mark.asyncio
async def test_fetch_data_retry_fails_after_max_retries(monkeypatch):
    """Test that after max retries, the error is raised."""
    client = YFinanceClient()
    call_count = [0]
    
    async def fake_to_thread(*args, **kwargs):
        call_count[0] += 1
        # Always fail
        raise asyncio.TimeoutError("Transient timeout")
    
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    
    with pytest.raises(HTTPException) as excinfo:
        await client._fetch_data("info", lambda: None, "AAPL")
    
    assert excinfo.value.status_code == 503
    # Should have tried max_retries + 1 times
    assert call_count[0] == Settings().max_retries + 1


@pytest.mark.asyncio
async def test_fetch_data_retry_with_exponential_backoff(monkeypatch):
    """Test that exponential backoff with jitter is applied."""
    client = YFinanceClient()
    call_count = [0]
    sleep_times = []
    
    async def fake_to_thread(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 2:
            # First two calls fail
            raise asyncio.TimeoutError("Transient timeout")
        # Third call succeeds
        return {"data": "success"}
    
    async def fake_sleep(seconds):
        sleep_times.append(seconds)
    
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    
    result = await client._fetch_data("info", lambda: None, "AAPL")
    
    assert result == {"data": "success"}
    assert call_count[0] == 3  # Should have tried 3 times
    assert len(sleep_times) == 2  # Should have slept 2 times
    
    # Check that sleep times are increasing (exponential backoff)
    # Each should be between backoff_base * 2^attempt and backoff_base * 2^attempt + backoff_base * 2^attempt
    base = Settings().retry_backoff_base
    max_backoff = Settings().retry_backoff_max
    
    # First sleep should be between base and base*2
    assert sleep_times[0] >= base
    assert sleep_times[0] <= base * 2
    
    # Second sleep should be between base*2 and base*4 (with jitter)
    assert sleep_times[1] >= base * 2
    assert sleep_times[1] <= base * 4


@pytest.mark.asyncio
async def test_fetch_data_connection_error_retries(monkeypatch):
    """Test that ConnectionError is treated as transient and retried."""
    client = YFinanceClient()
    call_count = [0]
    
    async def fake_to_thread(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 2:
            # First call fails with ConnectionError
            raise ConnectionError("Network unreachable")
        # Second call succeeds
        return {"data": "success"}
    
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    
    result = await client._fetch_data("info", lambda: None, "AAPL")
    
    assert result == {"data": "success"}
    assert call_count[0] == 2


@pytest.mark.asyncio
async def test_fetch_data_unexpected_error_no_retry(monkeypatch):
    """Test that unexpected errors (non-transient) do not retry."""
    client = YFinanceClient()
    call_count = [0]
    
    async def fake_to_thread(*args, **kwargs):
        call_count[0] += 1
        # Non-transient error
        raise ValueError("Invalid data format")
    
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    
    with pytest.raises(HTTPException) as excinfo:
        await client._fetch_data("info", lambda: None, "AAPL")
    
    assert excinfo.value.status_code == 500
    assert call_count[0] == 1  # Should only try once for non-transient errors


@pytest.mark.asyncio
async def test_fetch_data_http_exception_no_retry(monkeypatch):
    """Test that HTTPExceptions are not retried."""
    client = YFinanceClient()
    call_count = [0]
    
    async def fake_to_thread(*args, **kwargs):
        call_count[0] += 1
        raise HTTPException(status_code=400, detail="Bad request")
    
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    
    with pytest.raises(HTTPException) as excinfo:
        await client._fetch_data("info", lambda: None, "AAPL")
    
    assert excinfo.value.status_code == 400
    assert call_count[0] == 1  # Should only try once for HTTPExceptions


@pytest.mark.asyncio
async def test_fetch_data_max_backoff_capped(monkeypatch):
    """Test that backoff time is capped at max backoff."""
    client = YFinanceClient()
    call_count = [0]
    sleep_times = []
    
    async def fake_to_thread(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 3:
            # Fail 3 times to test max backoff (with 3 retries, we get 4 attempts total)
            raise asyncio.TimeoutError("Transient timeout")
        return {"data": "success"}
    
    async def fake_sleep(seconds):
        sleep_times.append(seconds)
    
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    
    result = await client._fetch_data("info", lambda: None, "AAPL")
    
    assert result == {"data": "success"}
    max_backoff = Settings().retry_backoff_max
    
    # All sleep times should be <= max_backoff
    for sleep_time in sleep_times:
        assert sleep_time <= max_backoff


@pytest.mark.asyncio
async def test_get_info_non_dict(monkeypatch):
    """Simulate malformed info (non-dict) -> should raise HTTP 502."""
    client = YFinanceClient()
    ticker_mock = type("TickerMock", (), {"get_info": lambda self: ["invalid"]})()

    async def mock_get_ticker(symbol):
        return ticker_mock

    monkeypatch.setattr(client, "_get_ticker", mock_get_ticker)

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
    ticker_mock = type("TickerMock", (), {"get_info": lambda self: None})()

    async def mock_get_ticker(symbol):
        return ticker_mock

    monkeypatch.setattr(client, "_get_ticker", mock_get_ticker)

    async def mock_fetch_data(*a, **kw):
        return None

    monkeypatch.setattr(client, "_fetch_data", mock_fetch_data)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_info("AAPL")

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_news_non_list(monkeypatch):
    """Simulate malformed news (not a list) -> should raise HTTP 502."""
    client = YFinanceClient()
    ticker_mock = type("TickerMock", (), {"get_news": lambda self, **kw: {"not": "list"}})()

    async def mock_get_ticker(*args, **kwargs):
        return ticker_mock

    monkeypatch.setattr(client, "_get_ticker", mock_get_ticker)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_news("AAPL", 5, "news")

    assert excinfo.value.status_code == 502


@pytest.mark.asyncio
async def test_get_news_empty_list(monkeypatch):
    """Simulate empty news list -> should raise HTTP 404."""
    client = YFinanceClient()
    ticker_mock = type("TickerMock", (), {"get_news": lambda self, **kw: []})()

    async def mock_get_ticker(*args, **kwargs):
        return ticker_mock

    monkeypatch.setattr(client, "_get_ticker", mock_get_ticker)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_news("AAPL", 5, "news")

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_get_history_empty_df(monkeypatch):
    """Simulate empty history -> should raise HTTP 404."""
    client = YFinanceClient()
    ticker_mock = type("TickerMock", (), {"history": lambda self, **kw: pd.DataFrame()})()
    empty_df = pd.DataFrame()

    async def mock_get_ticker(symbol):
        return ticker_mock

    monkeypatch.setattr(client, "_get_ticker", mock_get_ticker)

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
    ticker_mock = type("TickerMock", (), {"history": lambda self, **kw: {"not": "df"}})()

    async def mock_get_ticker(symbol):
        return ticker_mock

    monkeypatch.setattr(client, "_get_ticker", mock_get_ticker)

    async def mock_fetch_data(*a, **kw):
        return {"not": "df"}

    monkeypatch.setattr(client, "_fetch_data", mock_fetch_data)

    with pytest.raises(HTTPException) as excinfo:
        await client.get_history("AAPL", None, None)

    assert excinfo.value.status_code == 502


@pytest.mark.asyncio
@pytest.mark.usefakeclient
async def test_historical_fake_client(client_fake):
    """Uses the fake deterministic client instead of async mocks."""
    resp = client_fake.get("/historical/AAPL", params={"interval": "1d"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert len(data["prices"]) == 3
    assert data["prices"][0]["open"] == 100.0
