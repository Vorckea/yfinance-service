"""Client for interacting with the Yahoo Finance API.

This module provides a robust, production-ready client for fetching financial data
from Yahoo Finance. It implements several resilience patterns including request
coalescing (deduplication of concurrent identical requests), exponential backoff
retry logic with jitter, and proper error handling.

Example:
    Basic usage of the client:

    >>> client = YFinanceClient()
    >>> info = await client.get_info("AAPL")
    >>> history = await client.get_history("AAPL", start=date(2023, 1, 1))
"""

import asyncio
import random
import socket
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from functools import lru_cache, partial
from typing import Any, Optional, TypeVar, Dict

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from app.clients.interface import YFinanceClientInterface
from app.settings import Settings

from ..monitoring.instrumentation import observe
from ..utils.logger import logger

YFinanceData = dict[str, Any]
T = TypeVar("T")
@dataclass
class _InflightEntry:
    """Represents an in-flight request with its result future.

    This internal dataclass tracks the state of a coalesced request, including
    the future that all waiters await, the reference count of waiters, and
    the background task driving the upstream fetch.

    Attributes:
        future: The asyncio Future that all waiters await for the result.
        ref_count: Number of waiters currently waiting for this request.
        task: Optional background task driving the upstream fetch. Only set
            for the leader request.
    """
    future: asyncio.Future
    ref_count: int  # Number of waiters for this request
    task: Optional[asyncio.Task] = None  # Background task driving the upstream fetch


def _safe_copy(value):
    """Shallow-copy dicts and DataFrames so coalesced callers can't corrupt each other.

    All waiters on a coalesced future receive the same underlying object from
    future.set_result(). Without copying, one caller mutating a dict or reindexing
    a DataFrame would silently corrupt every other caller's result.
    """
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, dict):
        return dict(value)
    return value


class YFinanceClient(YFinanceClientInterface):
    """Client for interacting with the Yahoo Finance API.

    Implements request coalescing to prevent thundering herd on the same symbol.
    Concurrent identical requests (same op and symbol) are deduplicated so only
    one upstream call is made and all callers await the same result.

    Also implements retry logic with exponential backoff for transient errors.

    The client maintains an LRU cache of yfinance Ticker objects to avoid
    recreating them for frequently accessed symbols.

    Attributes:
        _timeout: Maximum time in seconds to wait for a response from upstream.
        _get_ticker: Cached function for creating yfinance Ticker objects.
        _inflight: Dictionary tracking in-flight requests for coalescing.
        _inflight_lock: Async lock for thread-safe access to _inflight.
        _settings: Application settings including retry configuration.

    Example:
        >>> client = YFinanceClient(timeout=30, ticker_cache_size=512)
        >>> info = await client.get_info("MSFT")
        >>> print(info.get("marketCap"))
    """

    def __init__(self, timeout: int = 30, ticker_cache_size: int = 512,
                 max_upstream_concurrency: int = 10):
        """Initialize the YFinanceClient.

        Args:
            timeout: The maximum time in seconds to wait for a response from
                the Yahoo Finance API. Defaults to 30.
            ticker_cache_size: The maximum number of cached ticker objects.
                When the cache is full, the least recently used ticker is
                evicted. Defaults to 512.
            max_upstream_concurrency: Max simultaneous upstream calls.
                Also sizes the dedicated thread pool (2x for retry headroom).
                Defaults to 10.
        """
        import concurrent.futures as _cf
        self._timeout = timeout
        self._get_ticker = lru_cache(maxsize=ticker_cache_size)(self._ticker_factory)
        self._inflight: Dict[tuple, _InflightEntry] = {}
        self._inflight_lock = asyncio.Lock()
        self._settings = Settings()
        self._upstream_sem = asyncio.Semaphore(max_upstream_concurrency)
        # Dedicated pool isolates yfinance threads from the rest of the process.
        # 2x concurrency gives retries headroom without stalling new callers.
        self._executor = _cf.ThreadPoolExecutor(
            max_workers=max_upstream_concurrency * 2,
            thread_name_prefix="yfinance",
        )

    def _ticker_factory(self, symbol: str) -> yf.Ticker:
        """Create a new yfinance Ticker instance for the given symbol.

        This factory method is wrapped with lru_cache to avoid recreating
        Ticker objects for frequently accessed symbols.

        Args:
            symbol: The stock symbol (e.g., "AAPL", "MSFT").

        Returns:
            A configured yfinance Ticker instance.
        """
        return yf.Ticker(symbol)

    async def _get_ticker_maybe_async(self, symbol: str, *args, **kwargs) -> yf.Ticker:
        """Get a ticker instance, handling both sync and async variants.

        This method supports cases where _get_ticker has been patched or
        overridden with an async function (e.g., in tests). It detects
        whether the underlying call is async and awaits if necessary.

        Args:
            symbol: The stock symbol to get a ticker for.
            *args: Additional positional arguments passed to _get_ticker.
            **kwargs: Additional keyword arguments passed to _get_ticker.

        Returns:
            The yfinance Ticker instance.
        """
        if asyncio.iscoroutinefunction(self._get_ticker):
            return await self._get_ticker(symbol, *args, **kwargs)
        ticker = self._get_ticker(symbol)
        if asyncio.iscoroutine(ticker) or asyncio.isfuture(ticker):
            ticker = await ticker
        return ticker

    def _make_key(self, op: str, symbol: str, *args, **kwargs) -> tuple:
        """Create a cache key for request deduplication.

        Generates a unique key based on the operation type, symbol, and
        operation-specific parameters. This key is used to identify
        identical requests for coalescing.

        Args:
            op: The operation name (e.g., "history", "info", "news").
            symbol: The stock symbol.
            *args: Positional arguments specific to the operation.
            **kwargs: Keyword arguments specific to the operation.

        Returns:
            A tuple that uniquely identifies this request for coalescing purposes.
        """
        if op == "history":
            if args:
                if len(args) == 3:
                    start, end, interval = args
                elif len(args) == 1 and isinstance(args[0], tuple):
                    start, end, interval = args[0]
                else:
                    start, end, interval = (None, None, "1d")
            else:
                start = kwargs.get("start")
                end = kwargs.get("end")
                interval = kwargs.get("interval", "1d")
            return (op, symbol, str(start), str(end), interval)
        elif op in ("get_earnings", "earnings_dates", "quarterly_earnings", "income_stmt", "quarterly_income_stmt"):
            # Accept both "freq" (internal forwarding) and "frequency" (public API)
            freq = kwargs.get("freq") or kwargs.get("frequency", "quarterly")
            return (op, symbol, freq)
        elif op == "news":
            # count and tab alter the result; include them so differing requests don't coalesce
            count = kwargs.get("count", args[0] if args else None)
            tab = kwargs.get("tab", args[1] if len(args) > 1 else None)
            return (op, symbol, count, tab)
        elif op == "calendar":
            return (op, symbol)
        else:
            return (op, symbol)

    async def _fetch_data_coalesced(
        self, op: str, fetch_func, symbol: str, *args, **kwargs
    ):
        """Fetch data with request coalescing, upstream semaphore, and retry.

        The first concurrent caller for a given key is the "leader" and drives
        the upstream fetch. Every subsequent caller with the same key is a
        "follower" and awaits the same future. On resolution every caller
        receives an independent shallow copy so downstream mutations cannot
        corrupt other callers' data.

        The background task is wrapped in try/finally so the shared future is
        always settled and the inflight key always removed, even when the task
        is cancelled externally (e.g. app shutdown).
        """
        key = self._make_key(op, symbol, *args, **kwargs)

        async with self._inflight_lock:
            if key in self._inflight:
                entry = self._inflight[key]
                entry.ref_count += 1
                logger.debug(
                    "yfinance.client.coalesce.await",
                    extra={"symbol": symbol, "op": op, "waiters": entry.ref_count},
                )
                follower_future = entry.future
            else:
                loop = asyncio.get_running_loop()
                shared_future = loop.create_future()
                entry = _InflightEntry(future=shared_future, ref_count=1)
                self._inflight[key] = entry
                follower_future = None

        if follower_future is not None:
            # ── Follower path ─────────────────────────────────────────────────
            try:
                result = await asyncio.shield(follower_future)
                if hasattr(observe, "record_metric"):
                    observe.record_metric("YF_REQUESTS", 1, {"outcome": "cached_dedupe"})
                # Copy so this caller's mutations don't corrupt other waiters.
                return _safe_copy(result)
            except asyncio.CancelledError:
                async with self._inflight_lock:
                    if key in self._inflight and self._inflight[key].ref_count > 0:
                        self._inflight[key].ref_count -= 1
                raise

        # ── Leader path ───────────────────────────────────────────────────────
        async def _run_fetch():
            last_error = None
            max_retries = self._settings.max_retries
            resolved = False  # True once the shared future has been settled

            try:
                for attempt in range(max_retries + 1):
                    try:
                        async with observe(op):
                            async def _invoke_fetch():
                                # asyncio.to_thread keeps tests patchable via
                                # monkeypatch.setattr(asyncio, "to_thread", ...).
                                # functools.partial bundles **kwargs because
                                # to_thread only accepts positional extra args.
                                call_result = await asyncio.to_thread(
                                    partial(fetch_func, **kwargs), *args
                                )
                                if asyncio.iscoroutine(call_result) or asyncio.isfuture(call_result):
                                    return await call_result
                                return call_result

                            async with self._upstream_sem:
                                result = await asyncio.wait_for(
                                    _invoke_fetch(), self._timeout
                                )

                        async with self._inflight_lock:
                            _e = self._inflight.pop(key, None)
                            if _e and not _e.future.done():
                                _e.future.set_result(result)
                        resolved = True
                        return

                    except (ConnectionError, asyncio.TimeoutError, socket.timeout) as e:
                        last_error = e
                        if attempt < max_retries:
                            base_backoff = self._settings.retry_backoff_base * (2 ** attempt)
                            capped = min(base_backoff, self._settings.retry_backoff_max)
                            jitter = random.uniform(0, self._settings.retry_backoff_base)
                            sleep_time = capped + jitter
                            logger.debug(
                                "yfinance.client.retry",
                                extra={"symbol": symbol, "op": op,
                                       "attempt": attempt + 1, "backoff": sleep_time},
                            )
                            await asyncio.sleep(sleep_time)
                        else:
                            break

                    except asyncio.CancelledError:
                        logger.warning(
                            "yfinance.client.cancelled",
                            extra={"symbol": symbol, "op": op},
                        )
                        error = HTTPException(status_code=499, detail="Request cancelled")
                        await self._resolve_error(key, error)
                        resolved = True
                        return

                    except HTTPException as e:
                        await self._resolve_error(key, e)
                        resolved = True
                        return

                    except Exception as e:
                        logger.exception(
                            "yfinance.client.unexpected",
                            extra={"symbol": symbol, "op": op, "error": str(e)},
                        )
                        error = HTTPException(
                            status_code=500, detail="Unexpected error fetching data"
                        )
                        await self._resolve_error(key, error)
                        resolved = True
                        return

                # All retries exhausted
                if last_error:
                    logger.warning(
                        "yfinance.client.timeout",
                        extra={"symbol": symbol, "op": op, "error": str(last_error)},
                    )
                    error = HTTPException(status_code=503, detail="Upstream timeout")
                    await self._resolve_error(key, error)
                    resolved = True

            finally:
                # Safety net: settle the future and remove the key even when
                # _run_fetch is cancelled externally (app shutdown, test teardown,
                # KeyboardInterrupt). Without this, all followers hang forever.
                if not resolved:
                    logger.warning(
                        "yfinance.client.aborted",
                        extra={"symbol": symbol, "op": op},
                    )
                    async with self._inflight_lock:
                        _e = self._inflight.pop(key, None)
                        if _e and not _e.future.done():
                            _e.future.set_exception(
                                HTTPException(status_code=503, detail="Request aborted")
                            )

        # Register task inside the lock so no follower observes a missing task.
        async with self._inflight_lock:
            task = asyncio.create_task(_run_fetch())
            entry.task = task

        try:
            result = await asyncio.shield(entry.future)
            # Copy so the leader's caller can't corrupt the result for followers
            # who are still awaiting or will receive it from the future.
            return _safe_copy(result)
        except asyncio.CancelledError:
            async with self._inflight_lock:
                if key in self._inflight and self._inflight[key].ref_count > 0:
                    self._inflight[key].ref_count -= 1
                    if self._inflight[key].ref_count == 0 and self._inflight[key].task:
                        self._inflight[key].task.cancel()
            raise

    async def _resolve_error(self, key: tuple, error: HTTPException) -> None:
        """Resolve the in-flight future with an error and clean up.

        Called when an error occurs during fetching. Resolves the shared future
        with the error so all waiting followers receive it, and removes the
        entry from the in-flight tracking.

        Args:
            key: The cache key identifying the in-flight request.
            error: The HTTPException to resolve the future with.
        """
        async with self._inflight_lock:
            entry = self._inflight.pop(key, None)
            if entry and not entry.future.done():
                entry.future.set_exception(error)

    async def _fetch_data(
        self, op: str, fetch_func: Callable[..., T], symbol: str, *args, **kwargs
    ) -> T:
        """Legacy fetch method - now delegates to coalesced version.

        This method exists for backward compatibility. New code should use
        _fetch_data_coalesced directly.

        Args:
            op: The operation name.
            fetch_func: The function to call to fetch data.
            symbol: The stock symbol.
            *args: Positional arguments for fetch_func.
            **kwargs: Keyword arguments for fetch_func.

        Returns:
            The result of the fetch operation.
        """
        return await self._fetch_data_coalesced(op, fetch_func, symbol, *args, **kwargs)

    def _normalize(self, symbol: str) -> str:
        """Normalize a stock symbol to uppercase and strip whitespace.

        Args:
            symbol: The raw stock symbol string.

        Returns:
            The normalized symbol (uppercase, stripped). Returns empty string
            if symbol is None.
        """
        return (symbol or "").upper().strip()

    async def get_info(self, symbol: str) -> YFinanceData | None:
        """Fetch company information for a specific stock.

        Retrieves comprehensive information about a company including market cap,
        sector, industry, description, and other metadata.

        Args:
            symbol: The stock symbol (e.g., "AAPL", "MSFT").

        Returns:
            Dictionary containing company information, or None if not available.

        Raises:
            HTTPException: 404 if no data is found, 502 if the data format
                is invalid.
        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker_maybe_async(symbol)
        info = await self._fetch_data("info", ticker.get_info, symbol)
        if not info:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "info"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        if not isinstance(info, dict):
            logger.warning(
                "yfinance.client.invalid_info_type", extra={"symbol": symbol, "type": type(info)}
            )
            raise HTTPException(status_code=502, detail="Malformed data from upstream")
        return info

    async def get_news(self, symbol: str, count: int, tab: str) -> list[YFinanceData]:
        """Fetch news articles for a specific stock.

        Retrieves recent news articles related to the specified stock symbol.

        Args:
            symbol: The stock symbol (e.g., "AAPL").
            count: The maximum number of news articles to retrieve.
            tab: The news tab/category to fetch from.

        Returns:
            List of dictionaries containing news article data.

        Raises:
            HTTPException: 404 if no news is found, 502 if the data format
                is invalid.
        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker_maybe_async(symbol, no_cache=True)
        news = await self._fetch_data("news", ticker.get_news, symbol, count=count, tab=tab)
        if not news:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "news"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        if not isinstance(news, list):
            logger.warning(
                "yfinance.client.invalid_info_type", extra={"symbol": symbol, "type": type(news)},
            )
            raise HTTPException(status_code=502, detail="Malformed data form upstream")
        return news

    async def get_history(
        self, symbol: str, start: date | None, end: date | None, interval: str = "1d"
    ) -> pd.DataFrame | None:
        """Fetch historical market data for a specific stock.

        Retrieves OHLCV (Open, High, Low, Close, Volume) data for the specified
        date range and interval.

        Args:
            symbol: The stock symbol (e.g., "AAPL").
            start: The start date for historical data. If None, fetches from
                the earliest available date.
            end: The end date for historical data. If None, fetches up to
                the most recent data.
            interval: The data interval (e.g., "1d" for daily, "1wk" for weekly,
                "1mo" for monthly). Defaults to "1d".

        Returns:
            DataFrame with historical price data, or None if not available.

        Raises:
            HTTPException: 404 if no data is found, 502 if the data format
                is invalid.
        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker_maybe_async(symbol)
        history = await self._fetch_data(
            "history", ticker.history, symbol, start=start, end=end, interval=interval
        )
        if history is None:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "history"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        if not isinstance(history, pd.DataFrame):
            logger.warning(
                "yfinance.client.invalid_history_type",
                extra={"symbol": symbol, "type": type(history)},
            )
            raise HTTPException(status_code=502, detail="Malformed data from upstream")
        if history.empty:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "history"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        return history

    async def get_earnings(self, symbol: str, frequency: str = "quarterly") -> pd.DataFrame | None:
        """Fetch earnings data for a specific stock.

        Attempts to retrieve earnings data using multiple fallback methods:
        1. get_earnings() method if available
        2. earnings_dates property
        3. quarterly_earnings property
        4. Income statement data (income_stmt or quarterly_income_stmt)

        Args:
            symbol: The stock symbol (e.g., "AAPL").
            frequency: The frequency of earnings data - "quarterly" or "annual".
                Defaults to "quarterly".

        Returns:
            DataFrame with earnings data, or None if not available.

        Raises:
            HTTPException: If an HTTP error occurs during fetching.
        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker_maybe_async(symbol)

        try:
            if hasattr(ticker, "get_earnings"):
                df = await self._fetch_data(
                    "get_earnings",
                    lambda: ticker.get_earnings(
                        freq=frequency if frequency == "quarterly" else "annual"
                    ),
                    symbol,
                    freq=frequency,
                )
                if df is not None and (isinstance(df, pd.DataFrame) and not df.empty):
                    return df

            if hasattr(ticker, "earnings_dates"):
                df2 = await self._fetch_data(
                    "earnings_dates", lambda: ticker.earnings_dates, symbol
                )
                if df2 is not None and not df2.empty:
                    df2 = df2.reset_index().rename(columns={"index": "earnings_date"})
                    df2 = df2.set_index("earnings_date")
                    return df2

            if hasattr(ticker, "quarterly_earnings"):
                q = await self._fetch_data(
                    "quarterly_earnings", lambda: ticker.quarterly_earnings, symbol
                )
                if q is not None and isinstance(q, pd.DataFrame) and not q.empty:
                    return q
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "yfinance.client.earnings_try_failed", extra={"symbol": symbol, "error": str(e)}
            )

        try:
            if frequency == "annual":
                stmt = await self._fetch_data("income_stmt", lambda: ticker.income_stmt, symbol)
            else:
                stmt = await self._fetch_data(
                    "quarterly_income_stmt", lambda: ticker.quarterly_income_stmt, symbol
                )

            if stmt is None or stmt.empty:
                return None

            df_stmt = stmt.T.copy()
            df_stmt.index.name = "earnings_date"

            return df_stmt
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "yfinance.client.income_stmt_failed", extra={"symbol": symbol, "error": str(e)}
            )
            return None

    async def get_income_statement(self, symbol: str, frequency: str) -> pd.DataFrame | None:
        """Fetch income statement data for a specific stock.

        This is a convenience method that delegates to get_earnings.

        Args:
            symbol: The stock symbol (e.g., "AAPL").
            frequency: The frequency - "quarterly" or "annual".

        Returns:
            DataFrame with income statement data, or None if not available.
        """
        return await self.get_earnings(symbol, frequency)

    async def get_calendar(self, symbol: str) -> Dict[str, Any]:
        """Fetch earnings calendar data for a specific stock.

        Retrieves the earnings calendar which typically includes upcoming
        earnings dates, EPS estimates, and reported EPS.

        Args:
            symbol: The stock symbol (e.g., "AAPL").

        Returns:
            Dictionary containing calendar data.

        Raises:
            HTTPException: 404 if no data is found, 502 if the data format
                is invalid, 500 for other errors.
        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker_maybe_async(symbol)

        try:
            calendar_data = await self._fetch_data(
                op="calendar",
                fetch_func=lambda: ticker.calendar,
                symbol=symbol
            )

            if calendar_data is None:
                logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "calendar"})
                raise HTTPException(status_code=404, detail=f"No calendar data for {symbol}")

            if not isinstance(calendar_data, dict):
                logger.warning(
                    "yfinance.client.invalid_calendar_type",
                    extra={"symbol": symbol, "type": type(calendar_data)},
                )
                raise HTTPException(status_code=502, detail="Malformed data from upstream")

            return calendar_data

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "yfinance.client.calendar_failed", extra={"symbol": symbol, "error": str(e)}
            )
            raise HTTPException(status_code=500, detail="Failed to fetch calendar data") from e

    async def ping(self) -> bool:
        """Check if the Yahoo Finance API is reachable.

        Performs a lightweight health check by fetching basic info for a
        well-known stock (AAPL).

        Returns:
            True if the API is reachable and responding, False otherwise.
        """
        probe_symbol = "AAPL"
        try:
            ticker = await self._get_ticker_maybe_async(probe_symbol)
            await self._fetch_data("ping", ticker.get_info, probe_symbol)
            return True
        except HTTPException:
            return False

    async def get_splits(self, symbol: str) -> pd.Series:
        """Fetch stock split history for a specific stock.

        Retrieves historical stock split data including split dates and ratios.

        Args:
            symbol: The stock symbol (e.g., "AAPL").

        Returns:
            pandas Series with split data, indexed by date.

        Raises:
            HTTPException: 404 if no split data is found.
        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker_maybe_async(symbol)

        splits = await self._fetch_data("splits", lambda: ticker.splits, symbol)

        if splits is None or splits.empty:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol})
            raise HTTPException(
                status_code=404, 
                detail=f"No split data found for symbol: {symbol}"
            )

        return splits