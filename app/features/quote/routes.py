from fastapi import APIRouter, HTTPException
from fastapi.params import Query

from .models import QuoteResponse
from .service import fetch_quote

router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=QuoteResponse,
    summary="Get latest quote for a symbol",
    description="Returns the latest market quote for the given ticker symbol.",
)
async def get_quote(
    symbol: str = Query(..., description="Ticker symbol", example="AAPL"),
) -> QuoteResponse:
    """Get the latest market quote for a given ticker symbol."""
    try:
        return await fetch_quote(symbol)
    except HTTPException as e:
        raise e
