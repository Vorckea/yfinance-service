"""Models for historical stock data responses."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class HistoricalPrice(BaseModel):
    """Model for storing historical price data."""

    model_config = ConfigDict(frozen=True)

    date: datetime.date = Field(..., description="Date of the price")
    timestamp: datetime.datetime = Field(..., description="Timestamp of the price")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: int | None = Field(..., description="Trading volume")


class HistoricalResponse(BaseModel):
    """Response model for historical stock data."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    prices: list[HistoricalPrice] = Field(..., description="List of historical prices")
