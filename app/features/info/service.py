import asyncio
import re

import yfinance as yf
from fastapi import HTTPException

from ...utils.logger import logger
from .models import InfoResponse

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9\.\-]{1,10}$")


async def fetch_info(symbol: str) -> InfoResponse:
    logger.info("Info request received", extra={"symbol": symbol})
    if not SYMBOL_PATTERN.match(symbol):
        logger.error("Invalid symbol format", extra={"symbol": symbol})
        raise HTTPException(
            status_code=400,
            detail="Symbol must be 1-10 chars, alphanumeric, dot or dash.",
        )

    def fetch_info_data(symbol: str):
        ticker = yf.Ticker(symbol)
        return ticker.info

    try:
        info = await asyncio.to_thread(fetch_info_data, symbol)
    except Exception as e:
        logger.exception(
            f"Exception fetching info data. ({type(e).__name__}): {e}", extra={"symbol": symbol}
        )
        raise HTTPException(status_code=500, detail="Internal error fetching info data")

    if not info:
        logger.error("No data found", extra={"symbol": symbol})
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    logger.info("Info data fetched", extra={"symbol": symbol})
    return InfoResponse(
        symbol=symbol.upper(),
        short_name=info.get("shortName"),
        long_name=info.get("longName"),
        exchange=info.get("exchange"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        country=info.get("country"),
        website=info.get("website"),
        description=info.get("longBusinessSummary"),
        market_cap=info.get("marketCap"),
        shares_outstanding=info.get("sharesOutstanding"),
        dividend_yield=info.get("dividendYield"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        current_price=info.get("currentPrice"),
        trailing_pe=info.get("trailingPE"),
        beta=info.get("beta"),
        address=info.get("address1"),
    )
