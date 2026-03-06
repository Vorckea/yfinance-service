"""Tests for YFinanceClient request coalescing functionality."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import pandas as pd
from fastapi import HTTPException

from app.clients.yfinance_client import YFinanceClient, _InflightEntry


class TestRequestCoalescing:
    """Test suite for request coalescing (deduplication) functionality."""

    @pytest.fixture
    def client(self):
        """Create a fresh YFinanceClient for each test."""
        return YFinanceClient(timeout=30, ticker_cache_size=512)

    @pytest.fixture
    def mock_ticker(self):
        """Create a mock yfinance Ticker."""
        ticker = MagicMock()
        ticker.get_info.return_value = {"symbol": "AAPL", "name": "Apple Inc."}
        return ticker

    @pytest.mark.asyncio
    async def test_concurrent_identical_requests_deduplicated(self, client, mock_ticker):
        """Test that concurrent identical requests are coalesced into one upstream call."""
        call_count = 0

        async def slow_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow upstream
            return {"symbol": "AAPL", "name": "Apple Inc."}

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            with patch.object(mock_ticker, 'get_info', side_effect=slow_fetch):
                # Launch 10 concurrent requests for the same symbol
                tasks = [client.get_info("AAPL") for _ in range(10)]
                results = await asyncio.gather(*tasks)

        # Only one upstream call should have been made
        assert call_count == 1, f"Expected 1 upstream call, got {call_count}"

        # All results should be identical
        for result in results:
            assert result == {"symbol": "AAPL", "name": "Apple Inc."}

    @pytest.mark.asyncio
    async def test_concurrent_different_symbols_not_deduplicated(self, client, mock_ticker):
        """Test that requests for different symbols are not coalesced."""
        call_count = 0

        async def slow_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return {"symbol": "SYM", "name": f"Company {call_count}"}

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            with patch.object(mock_ticker, 'get_info', side_effect=slow_fetch):
                # Launch concurrent requests for different symbols
                tasks = [
                    client.get_info("AAPL"),
                    client.get_info("GOOGL"),
                    client.get_info("MSFT"),
                ]
                results = await asyncio.gather(*tasks)

        # Each symbol should get its own upstream call
        assert call_count == 3, f"Expected 3 upstream calls, got {call_count}"

    @pytest.mark.asyncio
    async def test_concurrent_different_ops_not_deduplicated(self, client):
        """Test that requests for different operations are not coalesced."""
        info_calls = 0
        history_calls = 0

        mock_ticker = MagicMock()

        async def slow_info(*args, **kwargs):
            nonlocal info_calls
            info_calls += 1
            await asyncio.sleep(0.05)
            return {"symbol": "AAPL"}

        async def slow_history(*args, **kwargs):
            nonlocal history_calls
            history_calls += 1
            await asyncio.sleep(0.05)
            return pd.DataFrame({"Close": [150.0]})

        mock_ticker.get_info = slow_info
        mock_ticker.history = slow_history

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            tasks = [
                client.get_info("AAPL"),
                client.get_history("AAPL", None, None, "1d"),
            ]
            await asyncio.gather(*tasks)

        assert info_calls == 1
        assert history_calls == 1

    @pytest.mark.asyncio
    async def test_error_propagation_to_all_waiters(self, client, mock_ticker):
        """Test that errors are properly propagated to all waiting coalesced requests."""
        call_count = 0

        async def failing_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            raise ConnectionError("Network error")

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            with patch.object(mock_ticker, 'get_info', side_effect=failing_fetch):
                tasks = [client.get_info("AAPL") for _ in range(5)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one upstream call should have been made
        assert call_count == 1

        # All results should be HTTPException with 503 status
        for result in results:
            assert isinstance(result, HTTPException)
            assert result.status_code == 503
            assert "timeout" in result.detail.lower() or "upstream" in result.detail.lower()

    @pytest.mark.asyncio
    async def test_cancellation_handling(self, client, mock_ticker):
        """Test that cancellation is handled correctly for coalesced requests."""
        call_count = 0

        async def slow_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.5)  # Long delay to allow cancellation
            return {"symbol": "AAPL"}

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            with patch.object(mock_ticker, 'get_info', side_effect=slow_fetch):
                # Start multiple concurrent requests
                task1 = asyncio.create_task(client.get_info("AAPL"))
                task2 = asyncio.create_task(client.get_info("AAPL"))
                task3 = asyncio.create_task(client.get_info("AAPL"))

                # Let them start
                await asyncio.sleep(0.01)

                # Cancel the second task
                task2.cancel()

                try:
                    await task2
                except asyncio.CancelledError:
                    pass

                # Others should still complete successfully
                result1 = await task1
                result3 = await task3

                assert result1 == {"symbol": "AAPL"}
                assert result3 == {"symbol": "AAPL"}
                assert call_count == 1

    @pytest.mark.asyncio
    async def test_sequential_requests_not_deduplicated(self, client, mock_ticker):
        """Test that sequential (non-concurrent) requests are not deduplicated."""
        call_count = 0

        async def quick_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"symbol": "AAPL", "call": call_count}

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            with patch.object(mock_ticker, 'get_info', side_effect=quick_fetch):
                # Sequential calls
                result1 = await client.get_info("AAPL")
                result2 = await client.get_info("AAPL")
                result3 = await client.get_info("AAPL")

        # Each call should execute separately
        assert call_count == 3
        assert result1["call"] == 1
        assert result2["call"] == 2
        assert result3["call"] == 3

    @pytest.mark.asyncio
    async def test_history_deduplication_with_same_params(self, client):
        """Test that history requests with same params are coalesced."""
        call_count = 0

        mock_ticker = MagicMock()

        async def slow_history(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return pd.DataFrame({"Close": [150.0, 151.0]})

        mock_ticker.history = slow_history

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            tasks = [
                client.get_history("AAPL", start_date, end_date, "1d")
                for _ in range(5)
            ]
            results = await asyncio.gather(*tasks)

        assert call_count == 1
        for result in results:
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_history_not_deduplicated_with_different_params(self, client):
        """Test that history requests with different params are not coalesced."""
        call_count = 0

        mock_ticker = MagicMock()

        async def slow_history(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return pd.DataFrame({"Close": [150.0]})

        mock_ticker.history = slow_history

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            tasks = [
                client.get_history("AAPL", date(2024, 1, 1), date(2024, 1, 31), "1d"),
                client.get_history("AAPL", date(2024, 2, 1), date(2024, 2, 28), "1d"),
                client.get_history("AAPL", date(2024, 1, 1), date(2024, 1, 31), "1wk"),
            ]
            await asyncio.gather(*tasks)

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_inflight_cleanup_on_success(self, client):
        """Test that in-flight entries are cleaned up after successful completion."""
        mock_ticker = MagicMock()
        mock_ticker.get_info = AsyncMock(return_value={"symbol": "AAPL"})

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            await client.get_info("AAPL")

            # In-flight map should be empty after completion
            assert len(client._inflight) == 0

    @pytest.mark.asyncio
    async def test_inflight_cleanup_on_error(self, client, mock_ticker):
        """Test that in-flight entries are cleaned up after error."""
        async def failing_fetch(*args, **kwargs):
            raise ConnectionError("Network error")

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            with patch.object(mock_ticker, 'get_info', side_effect=failing_fetch):
                with pytest.raises(HTTPException):
                    await client.get_info("AAPL")

            # In-flight map should be empty after error
            assert len(client._inflight) == 0

    @pytest.mark.asyncio
    async def test_mixed_success_and_cancellation(self, client, mock_ticker):
        """Test complex scenario with multiple concurrent requests, some cancelled."""
        call_count = 0

        async def slow_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.2)
            return {"symbol": "AAPL", "data": "value"}

        with patch.object(client, '_get_ticker', return_value=mock_ticker):
            with patch.object(mock_ticker, 'get_info', side_effect=slow_fetch):
                # Create many concurrent tasks
                tasks = [asyncio.create_task(client.get_info("AAPL")) for _ in range(10)]

                # Let them start coalescing
                await asyncio.sleep(0.01)

                # Cancel half of them
                for i in range(5):
                    tasks[i].cancel()

                # Wait for all to complete
                results = []
                for i, task in enumerate(tasks):
                    try:
                        result = await task
                        results.append((i, "success", result))
                    except asyncio.CancelledError:
                        results.append((i, "cancelled", None))
                    except HTTPException as e:
                        results.append((i, "error", e))

        # Only one upstream call
        assert call_count == 1

        # Check results
        cancelled_count = sum(1 for r in results if r[1] == "cancelled")
        success_count = sum(1 for r in results if r[1] == "success")

        assert cancelled_count == 5
        assert success_count == 5

        # All successful results should have the same data
        for r in results:
            if r[1] == "success":
                assert r[2] == {"symbol": "AAPL", "data": "value"}


class TestInflightKeyGeneration:
    """Test suite for in-flight key generation."""

    @pytest.fixture
    def client(self):
        return YFinanceClient()

    def test_info_key(self, client):
        """Test key generation for info operation."""
        key = client._make_key("info", "AAPL")
        assert key == ("info", "AAPL")

    def test_history_key_with_dates(self, client):
        """Test key generation for history with date parameters."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        key = client._make_key("history", "AAPL", start, end, "1d")
        assert key == ("history", "AAPL", "2024-01-01", "2024-01-31", "1d")

    def test_history_key_different_intervals(self, client):
        """Test that different intervals produce different keys."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        key1 = client._make_key("history", "AAPL", start, end, "1d")
        key2 = client._make_key("history", "AAPL", start, end, "1wk")
        assert key1 != key2

    def test_earnings_key(self, client):
        """Test key generation for earnings operations."""
        key_quarterly = client._make_key("get_earnings", "AAPL")
        key_annual = client._make_key("get_earnings", "AAPL", freq="annual")
        assert key_quarterly != key_annual

    def test_calendar_key(self, client):
        """Test key generation for calendar operation."""
        key = client._make_key("calendar", "AAPL")
        assert key == ("calendar", "AAPL")
