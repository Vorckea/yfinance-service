"""Tests for the `/info` endpoint using fixtures and parametrization.

These tests follow best practices: shared test data in a feature-scoped
fixture, clear assertions on response shape and types, and parametrized
error cases.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.features.info.models import InfoResponse
from app.features.info.service import fetch_info
from app.utils.cache.ttl_in_memory import TTLCache

VALID_SYMBOL = "AAPL"
INVALID_SYMBOL = "!!!"
NOT_FOUND_SYMBOL = "ZZZZZZZZZZ"


def test_info_valid_symbol(client, mock_yfinance_client, info_payload_factory):
    """Valid symbol returns mapped info with expected fields and types.

    Parse the endpoint response into `InfoResponse` so tests follow the
    canonical model representation rather than relying on raw JSON keys or
    aliasing behavior.
    """
    mock_yfinance_client.get_info.return_value = info_payload_factory()

    resp = client.get(f"/info/{VALID_SYMBOL}")
    assert resp.status_code == 200

    info = InfoResponse.model_validate(resp.json())

    # Basic expected attributes and types (model fields)
    assert info.symbol == VALID_SYMBOL
    assert isinstance(info.short_name, str)
    assert isinstance(info.current_price, (int, float))
    assert isinstance(info.currency, str)

    # Spot-check values mapped from the fake info payload
    assert info.short_name == "Apple Inc."
    assert info.current_price == 150.0
    assert info.address == "1 Apple Park Way, Cupertino, CA 95014, USA"


@pytest.mark.asyncio
async def test_fetch_info_maps_fields_direct(fake_yfinance_client):
    """Unit test of `fetch_info` mapping using the deterministic fake client."""
    result = await fetch_info("AAPL", fake_yfinance_client, info_cache=None)

    assert isinstance(result, InfoResponse)
    assert result.symbol == "AAPL"
    # FakeYFinanceClient returns `shortName` as `Fake Company Inc.`
    assert result.short_name == "Fake Company Inc."


@pytest.mark.asyncio
async def test_fetch_info_uses_cache_hit(info_payload_factory):
    """When a cached InfoResponse exists, `fetch_info` should return it and not call the client."""
    # Prepare a cache pre-populated with an InfoResponse
    cache = TTLCache(size=4, ttl=60)
    # use factory (provided as fixture) to allow easy overrides if needed
    cached = InfoResponse.model_validate({"symbol": "AAPL", **info_payload_factory()})
    await cache.set("AAPL", cached)
    # use a mock client and assert it's not called

    client = AsyncMock()
    result = await fetch_info("AAPL", client, info_cache=cache)
    assert result is cached
    client.get_info.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_info_raises_on_none_from_client():
    """If the client returns None or a non-mapping, the service should raise an error.

    This guards against unexpected upstream responses and ensures the mapping step
    fails fast and loudly so the API layer can translate appropriately.
    """

    class BadClient:
        async def get_info(self, symbol: str):
            return None

    with pytest.raises(TypeError):
        await fetch_info("AAPL", BadClient(), info_cache=None)


@pytest.mark.asyncio
async def test_aliases_and_extra_fields_are_handled(info_payload_factory):
    """Ensure alias mapping and extra-field ignoring behave as expected."""
    payload = info_payload_factory(
        longBusinessSummary="desc", address1="addr", extraField="ignored"
    )

    class C:
        async def get_info(self, symbol: str):
            return payload

    res = await fetch_info("AAPL", C(), info_cache=None)
    assert isinstance(res, InfoResponse)
    assert res.description == "desc"
    assert res.address == "addr"
    # extra fields are not present on the model
    assert not hasattr(res, "extraField")


@pytest.mark.asyncio
async def test_cache_set_failure_is_logged(info_payload_factory, failing_cache, caplog):
    """If cache.set raises, the service should still return the InfoResponse and log the failure."""
    payload = info_payload_factory()

    class Client:
        async def get_info(self, symbol: str):
            return payload

    caplog.clear()
    res = await fetch_info("AAPL", Client(), info_cache=failing_cache)
    assert isinstance(res, InfoResponse)
    # ensure the cache failure is logged
    assert any("info.set.cache.failed" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test_cache_set_on_miss(fake_yfinance_client, info_payload_factory):
    cache = AsyncMock()
    cache.get.return_value = None
    _ = await fetch_info("AAPL", fake_yfinance_client, info_cache=cache)
    cache.set.assert_awaited_once()
    assert cache.set.call_args[0][0] == "AAPL"


@pytest.mark.parametrize(
    "symbol, expected_status",
    [
        (INVALID_SYMBOL, 422),
        (NOT_FOUND_SYMBOL, 404),
    ],
)
def test_info_errors(client, mock_yfinance_client, symbol, expected_status):
    """Parametrized tests for invalid and not-found symbol cases.

    For the not-found case we configure the client to raise an `HTTPException`.
    """
    if expected_status == 404:
        mock_yfinance_client.get_info.side_effect = HTTPException(
            status_code=404, detail=f"No data for {symbol}"
        )

    resp = client.get(f"/info/{symbol}")
    assert resp.status_code == expected_status

    body = resp.json()
    if expected_status == 422:
        assert "detail" in body and isinstance(body["detail"], list)
    else:
        assert "No data for" in str(body.get("detail", ""))
