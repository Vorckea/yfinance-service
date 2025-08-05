from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
    """Response model for stock quote data."""

    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    current_price: float | None = Field(None, description="Current market price")
    previous_close: float | None = Field(None, description="Previous closing price")
    open: float | None = Field(None, description="Opening price")
    high: float | None = Field(None, description="Highest price of the day")
    low: float | None = Field(None, description="Lowest price of the day")
    volume: int | None = Field(None, description="Trading volume")
