from unittest.mock import AsyncMock

import pytest


@pytest.fixture(scope="function")
def quote_payload_factory():
    base = {
        "symbol": "AAPL",
        "current_price": 150.0,
        "previous_close": 148.0,
        "open_price": 149.0,
        "high": 151.0,
        "low": 147.5,
        "volume": 1000000,
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