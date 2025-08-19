from pydantic import BaseModel, ConfigDict, Field


class QuoteResponse(BaseModel):
    """Response model for stock quote data."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    symbol: str = Field(
        ...,
        description="Ticker symbol",
        examples=["AAPL", "GOOGL", "MSFT"],
    )
    current_price: float = Field(
        ...,
        description="Current market price",
        examples=[150.0, 2800.0],
    )
    previous_close: float = Field(
        ...,
        description="Previous closing price",
        examples=[148.0, 2790.0],
    )
    open_price: float = Field(
        ...,
        description="Opening price",
        examples=[149.0, 2795.0],
    )
    high: float = Field(
        ...,
        description="Highest price of the day",
        examples=[151.0, 2805.0],
    )
    low: float = Field(
        ...,
        description="Lowest price of the day",
        examples=[147.5, 2785.0],
    )
    volume: int | None = Field(
        None,
        description="Trading volume",
        examples=[10000, 500000, None],
    )
