"""Earnings data models."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EarningRow(BaseModel):
    """A single earnings report row."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    earnings_date: date = Field(
        ...,
        description="Date of the earnings report",
        examples=["2024-01-30", "2024-04-25"],
    )
    reported_eps: Optional[float] = Field(
        None,
        description="Reported earnings per share",
        examples=[1.95, None],
    )
    estimated_eps: Optional[float] = Field(
        None,
        description="Estimated earnings per share before report",
        examples=[1.89, None],
    )
    surprise: Optional[float] = Field(
        None,
        description="Surprise amount (reported - estimated)",
        examples=[0.06, -0.02, None],
    )
    surprise_percent: Optional[float] = Field(
        None,
        description="Surprise as percentage",
        examples=[3.17, -1.05, None],
    )


class EarningsResponse(BaseModel):
    """Earnings history response for a symbol."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    symbol: str = Field(
        ...,
        description="Ticker symbol",
        examples=["AAPL", "MSFT"],
    )
    frequency: str = Field(
        ...,
        description="Earnings frequency (quarterly or annual)",
        examples=["quarterly", "annual"],
    )
    rows: list[EarningRow] = Field(
        default_factory=list,
        description="List of earnings reports",
    )
    next_earnings_date: Optional[date] = Field(
        None,
        description="Next expected earnings date if available",
        examples=["2024-07-30", None],
    )
    last_eps: Optional[float] = Field(
        None,
        description="Most recent reported EPS (convenience field)",
        examples=[1.95, None],
    )
