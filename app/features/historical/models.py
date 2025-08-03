import datetime

from pydantic import BaseModel, Field


class HistoricalPrice(BaseModel):
    date: datetime.date = Field(..., description="Date of the price")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")


class HistoricalResponse(BaseModel):
    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    prices: list[HistoricalPrice] = Field(..., description="List of historical prices")
