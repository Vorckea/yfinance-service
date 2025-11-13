"""A lightweight fake YFinance client for testing purposes."""

from datetime import datetime
import pandas as pd
from app.clients.yfinance_client import YFinanceClientInterface


class FakeYFinanceClient(YFinanceClientInterface):
    """Fake client implementing YFinanceClientInterface for stable testing."""

    async def get_info(self, symbol: str) -> dict:
        """Return deterministic fake stock info."""
        return {
            "symbol": symbol.upper(),
            "shortName": "Fake Company Inc.",
            "currency": "USD",
            "exchange": "FAKE",
            "marketCap": 123_456_789,
        }

    async def get_history(self, symbol: str, start=None, end=None, interval="1d"):
        """Return a fake DataFrame with predictable, simple data."""
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

    async def ping(self) -> bool:
        """Return a simple True to simulate availability."""
        return True
