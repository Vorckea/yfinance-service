"""Quote service: fetches latest market data via yfinance."""

from typing import Any, Mapping

from fastapi import HTTPException
from pydantic import ValidationError

from ...clients.interface import YFinanceClientInterface
from ...utils.logger import logger
from .models import QuoteResponse

Info = Mapping[str, Any]


def _ensure_info_present(info: Info | None, symbol: str) -> Info:
    if not info:
        logger.warning("quote.fetch.no_upstream_data", extra={"symbol": symbol})
        raise HTTPException(status_code=502, detail="No data from upstream")
    return info


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
