"""Models for stock information responses."""

from pydantic import BaseModel, ConfigDict, Field


class InfoResponse(BaseModel):
    """Model for storing information about the application."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    short_name: str | None = Field(None, description="Short company name")
    long_name: str | None = Field(None, description="Full company name")
    exchange: str | None = Field(None, description="Exchange where the stock is listed")
    sector: str | None = Field(None, description="Company sector")
    industry: str | None = Field(None, description="Company industry")
    country: str | None = Field(None, description="Country of the company")
    website: str | None = Field(None, description="Company website")
    description: str | None = Field(None, description="Business summary")
    market_cap: int | None = Field(None, description="Market capitalization")
    shares_outstanding: int | None = Field(None, description="Shares outstanding")
    dividend_yield: float | None = Field(None, description="Dividend yield")
    fifty_two_week_high: float | None = Field(None, description="52-week high price")
    fifty_two_week_low: float | None = Field(None, description="52-week low price")
    current_price: float | None = Field(None, description="Current market price")
    trailing_pe: float | None = Field(None, description="Trailing P/E ratio")
    beta: float | None = Field(None, description="Beta value")
    address: str | None = Field(None, description="Company address")
    currency: str | None = Field(None, description="Currency of the stock")
