"""Quote service: fetches latest market data via yfinance."""

from typing import Any

from fastapi import HTTPException

from ...clients.yfinance_client import YFinanceClient
from ...utils.logger import logger
from .models import QuoteResponse


def _map_quote(symbol: str, info: dict[str, Any]) -> QuoteResponse:
    try:
        required_fields = [
            "regularMarketPrice",
            "regularMarketPreviousClose",
            "regularMarketOpen",
            "regularMarketDayHigh",
            "regularMarketDayLow",
        ]
        missing = [
            field
            for field in required_fields
            if info.get(field) is None and info.get(field.replace("regularMarket", "")) is None
        ]
        if missing:
            logger.warning(
                "quote.fetch.missing_fields", extra={"symbol": symbol, "missing": missing}
            )
            raise HTTPException(
                status_code=502, detail=f"Missing required fields from upstream: {missing}"
            )
        return QuoteResponse(
            symbol=symbol.upper(),
            current_price=float(info.get("regularMarketPrice")),
            previous_close=float(
                info.get("regularMarketPreviousClose") or info.get("previousClose")
            ),
            open=float(info.get("regularMarketOpen") or info.get("open")),
            high=float(info.get("regularMarketDayHigh") or info.get("dayHigh")),
            low=float(info.get("regularMarketDayLow") or info.get("dayLow")),
            volume=int(info.get("regularMarketVolume") or info.get("volume"))
            if info.get("regularMarketVolume") or info.get("volume")
            else None,
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
