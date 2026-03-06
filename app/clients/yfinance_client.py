"""Client for interacting with the Yahoo Finance API."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any, Optional, TypeVar, Dict

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from app.clients.interface import YFinanceClientInterface

from ..monitoring.instrumentation import observe
from ..utils.logger import logger

YFinanceData = dict[str, Any]
T = TypeVar("T")


@dataclass
class _InflightEntry:
    """Represents an in-flight request with its result future."""
    future: asyncio.Future
    ref_count: int  # Number of waiters for this request
    task: Optional[asyncio.Task] = None  # Background task driving the upstream fetch


class YFinanceClient(YFinanceClientInterface):
    """Client for interacting with the Yahoo Finance API.

    Implements request coalescing to prevent thundering herd on the same symbol.
    Concurrent identical requests (same op and symbol) are deduplicated so only
    one upstream call is made and all callers await the same result.
    """

    def __init__(self, timeout: int = 30, ticker_cache_size: int = 512):
        """Initialize the YFinanceClient.

        Args:
            timeout (int, optional): The maximum time to wait for a response. Defaults to 30.
            ticker_cache_size (int, optional): The maximum number of cached ticker objects. Defaults
                to 512.

        """
        self._timeout = timeout
        self._get_ticker = lru_cache(maxsize=ticker_cache_size)(self._ticker_factory)        
        self._inflight: Dict[tuple, _InflightEntry] = {}        # In-flight request map: key=(op, symbol, args_key) -> _InflightEntry
        self._inflight_lock = asyncio.Lock()

    def _ticker_factory(self, symbol: str) -> yf.Ticker:
        return yf.Ticker(symbol)

    def _make_key(self, op: str, symbol: str, *args, **kwargs) -> tuple:
        """Create a cache key for deduplication.

        For history operations, includes start/end/interval in the key.
        For earnings, includes frequency.
        For other ops, just (op, symbol).
        """
        if op == "history":
            # history can be called either with positional args (internal) or keyword args (public API).
            # but some internal callers may pass them positionally. Ensure the cache key
            # includes the actual date/interval values so concurrent requests with different
            # parameters don't coalesce.
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

                start = kwargs.get("start")
                end = kwargs.get("end")
                interval = kwargs.get("interval", "1d")

            return (op, symbol, str(start), str(end), interval)
        elif op in ("get_earnings", "earnings_dates", "quarterly_earnings", "income_stmt", "quarterly_income_stmt"):
            freq = kwargs.get("freq", "quarterly")
            return (op, symbol, freq)
        elif op == "calendar":
            return (op, symbol)
        else:
            return (op, symbol)

    async def _fetch_data_coalesced(
        self, op: str, fetch_func: Callable[..., T], symbol: str, *args, **kwargs
    ) -> T:
        """Fetch data with request coalescing.

        If another request for the same (op, symbol) is in flight, await its result.
        Otherwise, execute the fetch and share the result with other waiters.
        """
        key = self._make_key(op, symbol, *args, **kwargs)

        async with self._inflight_lock:
            if key in self._inflight:
                entry = self._inflight[key]         # Request already in flight, increment ref count and await existing future
                entry.ref_count += 1
                logger.debug(
                    "yfinance.client.coalesce.await",
                    extra={"symbol": symbol, "op": op, "waiters": entry.ref_count}
                )
                future = entry.future
            else:
                # Create new in-flight entry
                loop = asyncio.get_running_loop()
                future = loop.create_future()
                entry = _InflightEntry(future=future, ref_count=1)
                self._inflight[key] = entry
                future = None  # Mark as the leader (we'll execute the fetch)

        if future is not None:
            # We are a follower, await the leader's result.
            # Use shield() so that cancelling a waiter does not cancel the shared future.
            try:
                result = await asyncio.shield(future)
                # Record dedupe metric
                if hasattr(observe, 'record_metric'):
                    observe.record_metric("YF_REQUESTS", 1, {"outcome": "cached_dedupe"})
                return result
            except asyncio.CancelledError:
                # Propagate cancellation properly, but do not cancel the shared future.
                async with self._inflight_lock:
                    if key in self._inflight and self._inflight[key].ref_count > 0:
                        self._inflight[key].ref_count -= 1
                raise

        # We are the leader - start the upstream fetch in a background task and await the shared future.
        # This ensures that leader cancellation does not cancel the in-flight fetch for other waiters.

        async def _run_fetch():
            # Run the upstream fetch and resolve the shared future.
            try:
                async with observe(op):
                    # yfinance/lib may expose synchronous or asynchronous callables.
                    # We use a small helper to run the fetch and await any coroutine results.
                    async def _invoke_fetch():
                        call_result = await asyncio.to_thread(fetch_func, *args, **kwargs)
                        if asyncio.iscoroutine(call_result) or asyncio.isfuture(call_result):
                            return await call_result
                        return call_result

                    result = await asyncio.wait_for(_invoke_fetch(), self._timeout)

                async with self._inflight_lock:
                    entry = self._inflight.pop(key, None)
                    if entry and not entry.future.done():
                        entry.future.set_result(result)

            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                logger.warning(
                    "yfinance.client.timeout", extra={"symbol": symbol, "op": op, "error": str(e)}
                )
                error = HTTPException(status_code=503, detail="Upstream timeout")
                await self._resolve_error(key, error)

            except asyncio.CancelledError:
                # If the fetch task gets cancelled (e.g., because all waiters dropped), resolve the future as cancelled.
                logger.warning("yfinance.client.cancelled", extra={"symbol": symbol, "op": op})
                error = HTTPException(status_code=499, detail="Request cancelled")
                await self._resolve_error(key, error)

            except HTTPException as e:
                await self._resolve_error(key, e)

            except Exception as e:
                logger.exception(
                    "yfinance.client.unexpected", extra={"symbol": symbol, "op": op, "error": str(e)}
                )
                error = HTTPException(status_code=500, detail="Unexpected error fetching data")
                await self._resolve_error(key, error)

        # Start the background fetch task.
        # Store it so we can cancel it if all waiters abort.
        task = asyncio.create_task(_run_fetch())
        async with self._inflight_lock:
            # The entry should still exist by construction.
            current_entry = self._inflight.get(key)
            if current_entry:
                current_entry.task = task

        try:
            return await asyncio.shield(entry.future)
        except asyncio.CancelledError:
            # Caller cancelled. Decrement waiter count and maybe cancel the background fetch.
            async with self._inflight_lock:
                if key in self._inflight and self._inflight[key].ref_count > 0:
                    self._inflight[key].ref_count -= 1
                    if self._inflight[key].ref_count == 0 and self._inflight[key].task:
                        self._inflight[key].task.cancel()
            raise

    async def _resolve_error(self, key: tuple, error: HTTPException) -> None:
        """Resolve the in-flight future with an error and clean up."""
        async with self._inflight_lock:
            entry = self._inflight.pop(key, None)
            if entry and not entry.future.done():
                entry.future.set_exception(error)

    async def _fetch_data(
        self, op: str, fetch_func: Callable[..., T], symbol: str, *args, **kwargs
    ) -> T:
        """Legacy fetch method - now delegates to coalesced version."""
        return await self._fetch_data_coalesced(op, fetch_func, symbol, *args, **kwargs)

    def _normalize(self, symbol: str) -> str:
        return (symbol or "").upper().strip()

    async def get_info(self, symbol: str) -> YFinanceData | None:
        """Fetch information about a specific stock.

        Args:
            symbol (str): The stock symbol to fetch information for.

        Raises:
            HTTPException: If the symbol is not found or if there is an error fetching data.

        Returns:
            YFinanceData: The information about the stock.

        """
        symbol = self._normalize(symbol)
        ticker = self._get_ticker(symbol)
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

    async def get_history(
        self, symbol: str, start: date | None, end: date | None, interval: str = "1d"
    ) -> pd.DataFrame | None:
        """Fetch historical market data for a specific stock.

        Args:
            symbol (str): The stock symbol to fetch historical data for.
            start (date | None): The start date for the historical data.
            end (date | None): The end date for the historical data.
            interval (str): The data interval (e.g., "1d", "1h", "1wk"). Defaults to "1d".

        Raises:
            HTTPException: If the symbol is not found or if there is an error fetching data.

        Returns:
            pd.DataFrame: The historical market data for the stock.

        """
        symbol = self._normalize(symbol)
        ticker = self._get_ticker(symbol)
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
        symbol = self._normalize(symbol)
        ticker = self._get_ticker(symbol)

        try:

            if hasattr(ticker, "get_earnings"):
                df = await self._fetch_data(
                    "get_earnings",
                    lambda: ticker.get_earnings(
                        freq=frequency if frequency == "quarterly" else "annual"
                    ),
                    symbol,
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
        return await self.get_earnings(symbol, frequency)


    async def get_calendar(self, symbol: str) -> Dict[str, Any]:
        symbol = self._normalize(symbol)
        ticker = self._get_ticker(symbol)

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
        """Check if the YFinance API is reachable.

        Returns:
            bool: True if the API is reachable, False otherwise.

        """
        probe_symbol = "AAPL"
        try:
            await self._fetch_data("ping", self._get_ticker(probe_symbol).get_info, probe_symbol)
            return True
        except HTTPException:
            return False
