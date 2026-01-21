"""A lightweight fake YFinance client for testing purposes."""

from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd

from app.clients.interface import YFinanceClientInterface


class FakeYFinanceClient(YFinanceClientInterface):
    """Fake client implementing YFinanceClientInterface for stable testing."""

    async def get_info(self, symbol: str) -> Mapping[str, Any] | None:
        """Return deterministic fake stock info.

        Returns data in the format expected by yfinance, with all fields
        that the quote service might extract.
        """
        return {
            "symbol": symbol.upper(),
            "shortName": "Fake Company Inc.",
            "longName": "Fake Company Incorporated",
            "currency": "USD",
            "exchange": "NASDAQ",
            "marketCap": 123_456_789_000,
            "regularMarketPrice": 123.45,
            "regularMarketPreviousClose": 122.00,
            "regularMarketOpen": 123.00,
            "regularMarketDayHigh": 124.00,
            "regularMarketDayLow": 121.50,
            "regularMarketVolume": 1_000_000,
            "fiftyTwoWeekHigh": 150.00,
            "fiftyTwoWeekLow": 100.00,
            "sector": "Technology",
            "industry": "Software",
        }

    async def get_history(
        self, symbol: str, start: date | None = None, end: date | None = None, interval: str = "1d"
    ) -> pd.DataFrame | None:
        """Return a fake DataFrame with deterministic rows."""
        dates = pd.date_range(start or "2024-01-01", periods=3, freq="D")
        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0, 102.0],
                "High": [105.0, 106.0, 107.0],
                "Low": [99.0, 100.0, 101.0],
                "Close": [104.0, 105.0, 106.0],
                "Volume": [1000, 1100, 1200],
            },
            index=dates,
        )
        df.index.name = "Date"
        return df

    async def get_earnings(self, symbol: str, frequency: str = "quarterly") -> pd.DataFrame | None:
        """Return fake quarterly/annual earnings DataFrame."""
        if frequency == "annual":
            dates = pd.DatetimeIndex(["2024-01-30", "2023-01-31", "2022-01-28"])
            df = pd.DataFrame(
                {
                    "Reported EPS": [1.95, 1.81, 1.52],
                    "Estimated EPS": [1.89, 1.75, 1.50],
                    "Surprise": [0.06, 0.06, 0.02],
                    "Surprise %": [3.17, 3.43, 1.33],
                },
                index=dates,
            )
        else:
            dates = pd.DatetimeIndex(["2024-04-25", "2024-01-25", "2023-10-27", "2023-07-28"])
            df = pd.DataFrame(
                {
                    "Reported EPS": [1.95, 1.81, 1.52, 1.62],
                    "Estimated EPS": [1.89, 1.75, 1.50, 1.60],
                    "Surprise": [0.06, 0.06, 0.02, 0.02],
                    "Surprise %": [3.17, 3.43, 1.33, 1.25],
                },
                index=dates,
            )
        return df

    async def get_income_statement(self, symbol: str, frequency: str) -> pd.DataFrame | None:
        """Return a minimal deterministic income statement DataFrame."""
        dates = (
            pd.DatetimeIndex(["2024-12-31", "2023-12-31"])
            if frequency == "annual"
            else pd.DatetimeIndex(["2024-09-30", "2024-06-30", "2024-03-31"])
        )

        df = pd.DataFrame(
            {
                "Total Revenue": [10_000_000, 9_800_000, 9_500_000][: len(dates)],
                "Net Income": [2_000_000, 1_900_000, 1_850_000][: len(dates)],
            },
            index=dates,
        )
        return df

    async def get_calendar(self, symbol: str) -> Mapping[str, Any]:
        """Return deterministic fake earnings date."""
        return {
            "Earnings Date": [
                pd.Timestamp("2025-02-15", tz="UTC"),
            ]
        }

    async def ping(self) -> bool:
        """Return True to indicate the fake client is always available."""
        return True

    async def get_splits(self, symbol: str) -> pd.Series:
        """Deterministic fake implementation of the get_splits method."""
        import pandas as pd
        # Providing a default empty series prevents integration tests from crashing
        return pd.Series(dtype=float)

    async def get_news(self, symbol: str, count: int, tab: str) -> list[Mapping[str, Any]]:
        """Return deterministic fake news items."""
        return [
            {
                "id": "c3618287-ab77-4707-9611-2472b0a47a20",
                "content": {
                    "id": "c3618287-ab77-4707-9611-2472b0a47a20",
                    "contentType": "STORY",
                    "title": (
                        "Warren Buffett is stepping down as Berkshire Hathaway CEO."
                        "It's one of several big C-suite shake-ups in 2026."
                    ),
                    "description": "",
                    "summary": "These CEOs are taking the helm in 2026.",
                    "pubDate": "2025-12-31T17:56:38Z",
                    "displayTime": "2026-01-03T14:07:21Z",
                    "isHosted": "true",
                    "bypassModal": "false",
                    "previewUrl": "null"
                },
            },
        ]
