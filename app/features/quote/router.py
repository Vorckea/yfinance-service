"""Quote endpoint definitions.

Provides the /quote/{symbol} endpoint for fetching latest market data.
"""

from typing import Annotated, Dict, Union

from fastapi import APIRouter, Depends
from fastapi import HTTPException, Query
import asyncio
import json

from ...clients.interface import YFinanceClientInterface
from ...common.validation import SymbolParam
from ...dependencies import get_yfinance_client
from .models import QuoteResponse, SymbolErrorModel
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

MAX_CONCURRENCY = 10

@router.get(
    "",
    response_model=Dict[str, Union[QuoteResponse, SymbolErrorModel]],
    response_model_exclude_none=True,
    summary="Get latest quotes for multiple symbols",
    description="Accepts a CSV `symbols` query parameter and returns a map of symbol -> quote or error.",
    operation_id="getQuotesBulk",
)
async def get_quotes(
    symbols: Annotated[str, Query(..., description="Comma-separated list of ticker symbols")],
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)],
) -> Dict[str, Union[QuoteResponse, SymbolErrorModel]]:
    """Fetch latest quotes for multiple symbols in a single request.

    Behaviour:
    - Returns a mapping of SYMBOL -> QuoteResponse JSON for successful fetches.
    - For symbols that fail to fetch, the value will be an object with `error` and `status_code`.
    - The route returns HTTP 200 regardless of per-symbol failures; individual failures are reported per-symbol.
    """
    # Early guard for empty/whitespace-only param
    if not symbols or not symbols.strip():
        raise HTTPException(status_code=400, detail="Empty symbols list")

    # Parse CSV and normalize
    requested = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not requested:
        # catches inputs like ",,," or entries that are all whitespace
        raise HTTPException(status_code=400, detail="Empty symbols list")

    # Cap concurrency to avoid overwhelming upstream or local resources
    concurrency = min(len(requested), MAX_CONCURRENCY)
    semaphore = asyncio.BoundedSemaphore(concurrency)

    async def _fetch(sym: str):
        async with semaphore:
            try:
                result = await fetch_quote(sym, client)
                return sym, result
            except HTTPException as exc:
                # Sanitizing detail and status_code before constructing the Pydantic model
                detail = exc.detail
                try:
                    # Prioratize simple string representation; if complex, JSON-encode it
                    if isinstance(detail, (str, int, float, bool)):
                        err_str = str(detail)
                    else:
                        err_str = json.dumps(detail, default=str)
                except Exception:
                    err_str = str(detail)

                status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None) or 502
                try:
                    status_code = int(status_code)
                except Exception:
                    status_code = 502

                try:
                    return sym, SymbolErrorModel(error=err_str, status_code=status_code)
                except Exception:
                    # Fallback to plain dict if model construction unexpectedly fails
                    return sym, {"error": err_str, "status_code": status_code}
            except Exception as exc:  # pragma: no cover - defensive
                try:
                    return sym, SymbolErrorModel(error=str(exc), status_code=500)
                except Exception:
                    return sym, {"error": str(exc), "status_code": 500}

    tasks = [_fetch(s) for s in requested]
    results = await asyncio.gather(*tasks)

    # Build mapping
    out: dict[str, object] = {}
    for sym, value in results:
        # Pydantic models (QuoteResponse or SymbolErrorModel) expose model_dump
        if hasattr(value, "model_dump"):
            out[sym] = value.model_dump(exclude_none=True)
        else:
            out[sym] = value
    return out