from unittest.mock import AsyncMock

import pytest


@pytest.fixture(scope="function")
def info_payload_factory():
    base = {
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
        "website": "https://www.apple.com",
        "longBusinessSummary": (
            "Apple Inc. designs, manufactures, and markets consumer electronics, "
            "software, and services."
        ),
        "marketCap": 2500000000000,
        "sharesOutstanding": 16000000000,
        "dividendYield": 0.006,
        "fiftyTwoWeekHigh": 175.0,
        "fiftyTwoWeekLow": 120.0,
        "regularMarketPrice": 150.0,
        "currentPrice": 150.0,
        "trailingPE": 28.0,
        "beta": 1.2,
        "address1": "1 Apple Park Way, Cupertino, CA 95014, USA",
        "currency": "USD",
    }

    def _factory(**overrides):
        payload = base.copy()
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture(scope="function")
def failing_cache():
    c = AsyncMock()
    c.get.return_value = None
    c.set.side_effect = Exception("Cache failure")
    return c
