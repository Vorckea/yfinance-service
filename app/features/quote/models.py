"""Models for stock quote responses."""

from pydantic import (
    AliasChoices,
    AliasGenerator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)
from pydantic.alias_generators import to_camel


class QuoteResponse(BaseModel):
    """Response model for stock quote data."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        alias_generator=AliasGenerator(validation_alias=to_camel),
        populate_by_name=True,
    )

    symbol: str = Field(
        ...,
        description="Ticker symbol",
        examples=["AAPL", "GOOGL", "MSFT"],
    )
    current_price: float = Field(
        ...,
        description="Current market price",
        examples=[150.0, 2800.0],
        validation_alias=AliasChoices("regularMarketPrice", "currentPrice"),
    )
    previous_close: float = Field(
        ...,
        description="Previous closing price",
        examples=[148.0, 2790.0],
        validation_alias=AliasChoices("regularMarketPreviousClose", "previousClose"),
    )
    open_price: float = Field(
        ...,
        description="Opening price",
        examples=[149.0, 2795.0],
        validation_alias=AliasChoices("regularMarketOpen", "open"),
    )
    high: float = Field(
        ...,
        description="Highest price of the day",
        examples=[151.0, 2805.0],
        validation_alias=AliasChoices("regularMarketDayHigh", "dayHigh"),
    )
    low: float = Field(
        ...,
        description="Lowest price of the day",
        examples=[147.5, 2785.0],
        validation_alias=AliasChoices("regularMarketDayLow", "dayLow"),
    )
    volume: int | None = Field(
        None,
        description="Trading volume",
        examples=[10000, 500000, None],
        validation_alias=AliasChoices("regularMarketVolume", "volume"),
    )

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        """Ensure symbol is uppercase and stripped of whitespace."""
        return v.strip().upper()

    @field_validator("current_price", "previous_close", "open_price", "high", "low")
    @classmethod
    def non_negative(cls, v: float) -> float:
        """Ensure price fields are non-negative."""
        if v < 0:
            raise ValueError("must be non-negative")
        return v


class SymbolErrorModel(BaseModel):
    """Per-symbol error shape for bulk quote responses."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    error: str
    status_code: int
