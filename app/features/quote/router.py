"""Quote endpoint definitions.

Provides the /quote/{symbol} endpoint for fetching latest market data.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import HTTPException, Query
import asyncio

from ...clients.interface import YFinanceClientInterface
from ...common.validation import SymbolParam
from ...dependencies import get_yfinance_client
from .models import QuoteResponse
from .service import fetch_quote

router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=QuoteResponse,
    response_model_exclude_none=True,
    summary="Get latest quote for a symbol",
    description="Returns the latest market quote for the given ticker symbol.",
    operation_id="getQuoteBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "current_price": 150.0,
                        "previous_close": 148.0,
                        "open_price": 149.0,
                        "high": 151.0,
                        "low": 147.5,
                        "volume": 1000000,
                    }
                }
            },
        },
        404: {"description": "No quote data found for symbol"},
        422: {"description": "Validation error (invalid symbol format)"},
        499: {"description": "Request cancelled by client"},
        500: {"description": "Internal server error"},
        502: {"description": "Bad gateway"},
        503: {"description": "Upstream timeout"},
    },
)
async def get_quote(
    symbol: SymbolParam, client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)]
) -> QuoteResponse:
    """Get the latest market quote for a given ticker symbol."""
    return await fetch_quote(symbol, client)


@router.get(
    "",
    response_model_exclude_none=True,
    summary="Get latest quotes for multiple symbols",
    description="Accepts a CSV `symbols` query parameter and returns a map of symbol -> quote or error.",
    operation_id="getQuotesBulk",
)
async def get_quotes(
    symbols: Annotated[str, Query(..., description="Comma-separated list of ticker symbols")],
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)],
) -> dict:
    """Fetch latest quotes for multiple symbols in a single request.

    Behaviour:
    - Returns a mapping of SYMBOL -> QuoteResponse JSON for successful fetches.
    - For symbols that fail to fetch, the value will be an object with `error` and `status_code`.
    - The route returns HTTP 200 regardless of per-symbol failures; individual failures are reported per-symbol.
    """
    # Parse CSV and normalize
    requested = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not requested:
        raise HTTPException(status_code=400, detail="Empty symbols list")

    # Cap concurrency to avoid overwhelming upstream or local resources
    semaphore = asyncio.Semaphore(10)

    async def _fetch(sym: str):
        async with semaphore:
            try:
                result = await fetch_quote(sym, client)
                return sym, result
            except HTTPException as exc:
                return sym, {"error": str(exc.detail), "status_code": exc.status_code}
            except Exception as exc:  # pragma: no cover - defensive
                return sym, {"error": str(exc), "status_code": 500}

    tasks = [_fetch(s) for s in requested]
    results = await asyncio.gather(*tasks)

    # Build mapping
    out: dict[str, object] = {}
    for sym, value in results:
        # If it's a QuoteResponse, convert to dict
        if hasattr(value, "model_dump"):
            out[sym] = value.model_dump(exclude_none=True)
        else:
            out[sym] = value
    return out