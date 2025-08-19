"""Quote service: fetches latest market data via yfinance."""

from typing import Any

from fastapi import HTTPException

from ...clients.yfinance_client import YFinanceClient
from ...utils.logger import logger
from .models import QuoteResponse

FIELD_MAP = {
    "current_price": ["regularMarketPrice"],
    "previous_close": ["regularMarketPreviousClose", "previousClose"],
    "open": ["regularMarketOpen", "open"],
    "high": ["regularMarketDayHigh", "dayHigh"],
    "low": ["regularMarketDayLow", "dayLow"],
    "volume": ["regularMarketVolume", "volume"],
}

REQUIRED_FIELDS = ["current_price", "previous_close", "open", "high", "low"]


def _get_field(info: dict[str, Any], keys: list[str]) -> Any:
    """Return the first non-None value for the given keys from info."""
    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return None


def _validate_required_fields(info: dict[str, Any]) -> None:
    """Ensure all required fields are present in info."""
    missing = [field for field in REQUIRED_FIELDS if _get_field(info, FIELD_MAP[field]) is None]
    if missing:
        logger.warning("quote.fetch.missing_fields", extra={"missing": missing})
        raise HTTPException(
            status_code=502,
            detail=f"Missing required fields in upstream data: {', '.join(missing)}",
        )


def _parse_volume(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _map_quote(symbol: str, info: dict[str, Any]) -> QuoteResponse:
    try:
        _validate_required_fields(info)
        return QuoteResponse(
            symbol=symbol.upper(),
            current_price=float(_get_field(info, FIELD_MAP["current_price"])),
            previous_close=float(_get_field(info, FIELD_MAP["previous_close"])),
            open=float(_get_field(info, FIELD_MAP["open"])),
            high=float(_get_field(info, FIELD_MAP["high"])),
            low=float(_get_field(info, FIELD_MAP["low"])),
            volume=_parse_volume(_get_field(info, FIELD_MAP["volume"])),
        )
    except (TypeError, ValueError) as e:
        logger.warning("quote.fetch.malformed_data", extra={"symbol": symbol, "error": str(e)})
        raise HTTPException(status_code=502, detail="Malformed data from upstream")


async def fetch_quote(symbol: str, client: YFinanceClient) -> QuoteResponse:
    """Fetch stock quote information.

    Args:
        symbol (str): The stock symbol to fetch.
        client (YFinanceClient): The YFinance client to use for fetching data.

    Returns:
        QuoteResponse: The stock quote information.

    """
    symbol = symbol.upper().strip()
    logger.info("quote.fetch.start", extra={"symbol": symbol})

    info = await client.get_info(symbol)

    logger.info("quote.fetch.success", extra={"symbol": symbol})
    return _map_quote(symbol, info)
