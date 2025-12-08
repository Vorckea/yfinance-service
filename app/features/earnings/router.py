"""Earnings endpoint definitions."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from ...clients.interface import YFinanceClientInterface
from ...common.validation import SymbolParam
from ...dependencies import get_yfinance_client, get_earnings_cache
from ...utils.cache import SnapshotCache
from .models import EarningsResponse
from .service import fetch_earnings

router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=EarningsResponse,
    response_model_exclude_none=True,
    summary="Get earnings history for a symbol",
    description="Returns normalized earnings history (quarterly or annual) with reported/estimated EPS, revenue, and surprise data.",
    operation_id="getEarningsBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "frequency": "quarterly",
                        "rows": [
                            {
                                "earnings_date": "2024-04-25",
                                "reported_eps": 1.95,
                                "estimated_eps": 1.89,
                                "surprise": 0.06,
                                "surprise_percent": 3.17,
                            }
                        ],
                        "next_earnings_date": "2024-07-30",
                        "last_eps": 1.95,
                    }
                }
            },
        },
        404: {"description": "No earnings data found for symbol"},
        422: {"description": "Validation error (invalid symbol format)"},
        503: {"description": "Upstream timeout"},
    },
)
async def get_earnings(
    symbol: SymbolParam,
    frequency: Annotated[Literal["quarterly", "annual"], Query()] = "quarterly",
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)] = None,
    cache: Annotated[SnapshotCache, Depends(get_earnings_cache)] = None,
) -> EarningsResponse:
    """Get earnings history for a ticker symbol.

    Earnings data is cached by default (1-hour TTL, configurable via EARNINGS_CACHE_TTL env var).
    Set EARNINGS_CACHE_TTL=0 to disable caching.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT).
        frequency: 'quarterly' or 'annual'. Defaults to 'quarterly'.
        client: YFinance client (injected via dependency).
        cache: Earnings cache (injected via dependency).

    Returns:
        EarningsResponse with normalized earnings rows, next_earnings_date, and last_eps summary.
    """
    cache_key = f"{symbol.upper()}:{frequency}"
    
    # Use cache with get_or_set if cache is enabled
    if cache and cache._maxsize > 0:
        return await cache.get_or_set(cache_key, fetch_earnings(symbol, client, frequency))
    else:
        # No caching; fetch directly
        return await fetch_earnings(symbol, client, frequency)