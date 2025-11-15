"""A lightweight fake YFinance client for testing purposes."""

from datetime import datetime, timezone
import pandas as pd
from app.clients.yfinance_client import YFinanceClientInterface


class FakeYFinanceClient(YFinanceClientInterface):
    """Fake client implementing YFinanceClientInterface for stable testing."""
    
    _snapshot_cache = {}
    async def get_snapshot(self, symbol: str):
        if symbol in self._snapshot_cache:
            return self._snapshot_cache[symbol]

        data = {
            "symbol": symbol,
            "current_price": 123.45,
            "previous_close": 122.89,
            "open": 123.10,
            "high": 124.00,
            "low": 122.50,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "currency": "USD",
            "change": 0.56,
            "percent_change": 0.45,
            "volume": 1_000_000,
        }
        self._snapshot_cache[symbol] = data
        return data
    
    async def get_info(self, symbol: str) -> dict:
        """Return deterministic fake stock info."""
        # Provide both company info and quote-like fields so existing services
        # (`fetch_info` and `fetch_quote`) that expect `get_info` to contain
        # regularMarket* keys will work with this fake client.
        snapshot = await self.get_snapshot(symbol)
        return {
            "symbol": symbol.upper(),
            "shortName": "Fake Company Inc.",
            "currency": "USD",
            "exchange": "FAKE",
            "marketCap": 123_456_789,
            # Quote-like upstream keys expected by quote mapping
            "regularMarketPrice": snapshot["current_price"],
            "regularMarketPreviousClose": snapshot["previous_close"],
            "regularMarketOpen": snapshot["open"],
            "regularMarketDayHigh": snapshot["high"],
            "regularMarketDayLow": snapshot["low"],
            "regularMarketVolume": snapshot["volume"],
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
