"""Earnings data models."""

from pydantic import BaseModel, ConfigDict, Field
from datetime import date


class EarningRow(BaseModel):
    """A single earnings report row."""

    model_config = ConfigDict(extra= "ignore")

    earnings_date: date | None = Field(None, description="Date of the earnings report")
    reported_eps: float | None = Field(None, description="Reported earnings per share")
    estimated_eps: float | None = Field(
        None, description="Estimated earnings per share before report"
    )
    revenue: float | None = Field(None, description="Revenue for the period (if available)")
    surprise: float | None = Field(None, description="Surprise amount (reported - estimated)")
    surprise_percent: float | None = Field(None, description="Surprise as percentage")


class EarningsResponse(BaseModel):
    """Earnings history response for a symbol."""

    model_config = ConfigDict(extra= "ignore")

    symbol: str
    frequency: str
    rows: list[EarningRow]
    next_earnings_date: date | None = None
    last_eps: float | None = Field(
        default=None,
        description="The most recent non-null reported EPS from the earnings history"
    )
