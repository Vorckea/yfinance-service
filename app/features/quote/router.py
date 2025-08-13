"""Quote endpoint definitions.

Provides the /quote/{symbol} endpoint for fetching latest market data.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from ...clients.yfinance_client import YFinanceClient
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
                        "open": 149.0,
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
        503: {"description": "Upstream timeout"},
    },
)
async def get_quote(
    symbol: SymbolParam, client: Annotated[YFinanceClient, Depends(get_yfinance_client)]
) -> QuoteResponse:
    """Get the latest market quote for a given ticker symbol."""
    return await fetch_quote(symbol, client)
