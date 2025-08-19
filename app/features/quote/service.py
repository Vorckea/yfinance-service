"""Quote service: fetches latest market data via yfinance."""

from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import HTTPException

from ...clients.yfinance_client import YFinanceClient
from ...utils.logger import logger
from .models import QuoteResponse

FIELD_MAP: Mapping[str, Sequence[str]] = {
    "current_price": ["regularMarketPrice"],
    "previous_close": ["regularMarketPreviousClose", "previousClose"],
    "open": ["regularMarketOpen", "open"],
    "high": ["regularMarketDayHigh", "dayHigh"],
    "low": ["regularMarketDayLow", "dayLow"],
    "volume": ["regularMarketVolume", "volume"],
}

REQUIRED_FIELDS = ("current_price", "previous_close", "open", "high", "low")


def _get_field_by_name(info: dict[str, Any], field_name: str) -> Any:
    keys = FIELD_MAP.get(field_name, ())
    for key in keys:
        v = info.get(key)
        if v is not None:
            return v
    return None


def _ensure_info_present(info: dict[str, Any] | None, symbol: str) -> dict[str, Any]:
    if not info:
        logger.warning("quote.fetch.no_upstream_data", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="No data from upstream")
    return info


def _validate_required_fields(info: dict[str, Any]) -> None:
    missing = [f for f in REQUIRED_FIELDS if _get_field_by_name(info, f) is None]
    if missing:
        logger.warning("quote.fetch.missing_fields", extra={"missing": missing})
        raise HTTPException(
            status_code=502,
            detail=f"Missing required fields in upstream data: {', '.join(missing)}",
        )


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _map_quote(symbol: str, info: dict[str, Any]) -> QuoteResponse:
    _validate_required_fields(info)

    parsed: dict[str, float | None] = {}
    for logical in ("current_price", "previous_close", "open", "high", "low"):
        parsed[logical] = _parse_float(_get_field_by_name(info, logical))

    if any(
        parsed[name] is None for name in ("current_price", "previous_close", "open", "high", "low")
    ):
        logger.warning("quote.fetch.malformed_number", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="Malformed numeric data from upstream")

    volume = _parse_int(_get_field_by_name(info, "volume"))

    return QuoteResponse(
        symbol=symbol,
        current_price=parsed["current_price"],
        previous_close=parsed["previous_close"],
        open=parsed["open"],
        high=parsed["high"],
        low=parsed["low"],
        volume=volume,
    )


async def fetch_quote(symbol: str, client: YFinanceClient) -> QuoteResponse:
    """Fetch stock quote information.

    Args:
        symbol (str): The stock symbol to fetch.
        client (YFinanceClient): The YFinance client to use for fetching data.

    Returns:
        QuoteResponse: The stock quote information.

    """
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Empty symbol")

    logger.info("quote.fetch.start", extra={"symbol": symbol})

    info = await client.get_info(symbol)
    info = _ensure_info_present(info, symbol)

    logger.info("quote.fetch.success", extra={"symbol": symbol})
    return _map_quote(symbol, info)
