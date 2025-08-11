from pydantic import BaseModel, ConfigDict, Field


class QuoteResponse(BaseModel):
    """Response model for stock quote data."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    current_price: float = Field(..., description="Current market price")
    previous_close: float = Field(..., description="Previous closing price")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price of the day")
    low: float = Field(..., description="Lowest price of the day")
    volume: int | None = Field(..., description="Trading volume")
