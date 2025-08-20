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


def _map_quote(symbol: str, info: Info) -> QuoteResponse:
    mapped = _extract_logical_values(info)

    missing = [f for f in REQUIRED_FIELDS if mapped.get(f) is None]
    if missing:
        logger.warning("quote.fetch.missing_fields", extra={"missing": missing})
        raise HTTPException(
            status_code=502,
            detail=f"Missing required fields in upstream data: {', '.join(missing)}",
        )

    parse_float = _parse_float
    try:
        current = parse_float(mapped["current_price"])
        previous = parse_float(mapped["previous_close"])
        opened = parse_float(mapped["open"])
        high = parse_float(mapped["high"])
        low = parse_float(mapped["low"])
    except Exception:
        logger.warning("quote.fetch.malformed_number", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="Malformed numeric data from upstream")

    if any(x is None for x in (current, previous, opened, high, low)):
        logger.warning("quote.fetch.malformed_number", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="Malformed numeric data from upstream")

    volume = _parse_int(mapped.get("volume"))

    return QuoteResponse(
        symbol=symbol,
        current_price=current,
        previous_close=previous,
        open_price=opened,
        high=high,
        low=low,
        volume=volume,
    )


async def fetch_quote(symbol: str, client: YFinanceClientInterface) -> QuoteResponse:
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
