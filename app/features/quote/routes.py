from fastapi import APIRouter, HTTPException

from .models import QuoteResponse
from .service import fetch_quote

router = APIRouter()


@router.get("/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str) -> QuoteResponse:
    try:
        return await fetch_quote(symbol)
    except HTTPException as e:
        raise e
