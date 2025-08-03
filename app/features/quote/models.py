from pydantic import BaseModel


class QuoteResponse(BaseModel):
    symbol: str
    current_price: float | None
    previous_close: float | None
    open: float | None
    high: float | None
    low: float | None
    volume: int | None
