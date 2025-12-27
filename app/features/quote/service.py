"""Quote service: fetches latest market data via yfinance."""

from typing import Any, Mapping

from fastapi import HTTPException
from pydantic import ValidationError

from ...clients.interface import YFinanceClientInterface
from ...utils.logger import logger
from .models import QuoteResponse

Info = Mapping[str, Any]


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

    if not info:
        logger.info("quote.fetch.no_data", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="No data from upstream")

    try:
        mapped = QuoteResponse.model_validate({"symbol": symbol, **dict(info)})
    except ValidationError as exc:
        logger.warning(
            "quote.fetch.validation_error",
            extra={"symbol": symbol, "errors": exc.errors()},
        )
        raise HTTPException(
            status_code=502,
            detail=f"Malformed quote data from upstream for {symbol}",
        )

    logger.info("quote.fetch.success", extra={"symbol": symbol})
    return mapped
