"""Quote service: fetches latest market data via yfinance."""

from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import HTTPException

from ...clients.interface import YFinanceClientInterface
from ...utils.logger import logger
from .models import QuoteResponse

Info = dict[str, Any]

FIELD_MAP: Mapping[str, Sequence[str]] = {
    "current_price": ["regularMarketPrice"],
    "previous_close": ["regularMarketPreviousClose", "previousClose"],
    "open": ["regularMarketOpen", "open"],
    "high": ["regularMarketDayHigh", "dayHigh"],
    "low": ["regularMarketDayLow", "dayLow"],
    "volume": ["regularMarketVolume", "volume"],
}

REVERSE_MAP: dict[str, str] = {
    up_key: logical for logical, keys in FIELD_MAP.items() for up_key in keys
}

REQUIRED_FIELDS = ("current_price", "previous_close", "open", "high", "low")


def _extract_logical_values(info: Info) -> Info:
    result: Info = {}
    required_set = set(REQUIRED_FIELDS)

    for k, v in info.items():
        if v is None:
            continue
        logical = REVERSE_MAP.get(k)
        if logical and logical not in result:
            result[logical] = v
            if logical in required_set:
                required_set.discard(logical)
            if not required_set and "volume" in result:
                break
    return result


def _ensure_info_present(info: Info | None, symbol: str) -> Info:
    if not info:
        logger.warning("quote.fetch.no_upstream_data", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="No data from upstream")
    return info


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

def _raise_malformed_data(symbol: str) -> None:
    logger.warning("quote.fetch.malformed_number", extra={"symbol": symbol})
    raise HTTPException(
        status_code=502,
        detail=f"Malformed numeric data from upstream for {symbol}"
    )

def _map_quote(symbol: str, info: Info) -> QuoteResponse:
    """Map upstream info to QuoteResponse, validating required fields."""
    mapped = _extract_logical_values(info)

    # Check for missing required fields
    missing = [f for f in REQUIRED_FIELDS if mapped.get(f) is None]
    if missing:
        logger.warning(
            "quote.fetch.missing_fields",
            extra={"symbol": symbol, "missing": missing}
        )
        raise HTTPException(
            status_code=502,
            detail=f"Missing required fields in upstream data for {symbol}: {', '.join(missing)}",
        )

    # Parse required float fields in a loop
    parsed_values: dict[str, float] = {}
    for field in REQUIRED_FIELDS:
        value = _parse_float(mapped[field])
        if value is None:
            _raise_malformed_data(symbol)
        parsed_values[field] = value

    # Parse optional volume
    volume = _parse_int(mapped.get("volume"))
    if mapped.get("volume") is not None and volume is None:
        logger.warning("quote.fetch.malformed_volume", extra={"symbol": symbol})

    return QuoteResponse(
        symbol=symbol,
        current_price=parsed_values["current_price"],
        previous_close=parsed_values["previous_close"],
        open_price=parsed_values["open"],
        high=parsed_values["high"],
        low=parsed_values["low"],
        volume=volume,
    )



async def fetch_quote(symbol: str, client: YFinanceClientInterface) -> QuoteResponse:
    """Fetch stock quote information.

    Args:
        symbol (str): The stock symbol to fetch.
        client (YFinanceClient): The YFinance client to use for fetching data.

    Returns:
        QuoteResponse: The stock quote information.

    Raises:
        HTTPException: 400 for empty symbol, 502 for upstream issues.
    """
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Empty symbol")

    logger.info("quote.fetch.start", extra={"symbol": symbol})

    info = await client.get_info(symbol)
    info = _ensure_info_present(info, symbol)

    # Additional guard: fail if info is empty or all fields are None
    if not any(info.values()):
        logger.warning("quote.fetch.empty_upstream_data", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="Upstream data is empty")

    mapped = _map_quote(symbol, info)

    logger.info("quote.fetch.success", extra={"symbol": symbol})
    return mapped

