"""Snapshot endpoint definitions.

Provides the /snapshot/{symbol} endpoint for fetching combined info and quote data.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from ...clients.interface import YFinanceClientInterface
from ...common.validation import SymbolParam
from ...dependencies import get_info_cache, get_yfinance_client
from ...utils.cache import SnapshotCache
from .models import SnapshotResponse
from .service import fetch_snapshot

router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=SnapshotResponse,
    summary="Get snapshot (info + quote) for a symbol",
    description=(
        "Returns both company information and latest market quote for the given ticker symbol "
        "in a single response. If either info or quote fetch fails, the entire request returns 502. "
        "Info is cached with a 5-minute TTL; quote is always fresh."
    ),
    operation_id="getSnapshotBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "info": {
                            "symbol": "AAPL",
                            "short_name": "Apple Inc.",
                            "long_name": "Apple Inc.",
                            "exchange": "NASDAQ",
                            "sector": "Technology",
                            "industry": "Consumer Electronics",
                            "country": "United States",
                            "website": "https://www.apple.com",
                            "description": "Apple Inc. designs and manufactures consumer electronics.",
                            "market_cap": 2500000000000,
                            "shares_outstanding": 16000000000,
                            "dividend_yield": 0.006,
                            "fifty_two_week_high": 175.0,
                            "fifty_two_week_low": 120.0,
                            "current_price": 150.0,
                            "trailing_pe": 28.0,
                            "beta": 1.2,
                            "address": "1 Apple Park Way, Cupertino, CA 95014, USA",
                            "currency": "USD",
                        },
                        "quote": {
                            "symbol": "AAPL",
                            "current_price": 150.0,
                            "previous_close": 148.0,
                            "open_price": 149.0,
                            "high": 151.0,
                            "low": 147.5,
                            "volume": 1000000,
                        },
                    }
                }
            },
        },
        400: {"description": "Invalid request (e.g., empty symbol)"},
        422: {"description": "Validation error (invalid symbol format)"},
        499: {"description": "Request cancelled by client"},
        500: {"description": "Internal server error"},
        502: {"description": "Bad gateway (either info or quote fetch failed)"},
        503: {"description": "Upstream timeout"},
    },
)
async def get_snapshot(
    symbol: SymbolParam,
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)],
    info_cache: Annotated[SnapshotCache, Depends(get_info_cache)],
) -> SnapshotResponse:
    """Get both company information and latest market quote for a ticker symbol."""
    return await fetch_snapshot(symbol, client, info_cache)
