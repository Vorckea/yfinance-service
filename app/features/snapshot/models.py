"""Models for snapshot responses (combined info and quote)."""

from pydantic import BaseModel, ConfigDict, Field

from ..info.models import InfoResponse
from ..quote.models import QuoteResponse


class SnapshotResponse(BaseModel):
    """Composite response containing both info and quote data for a symbol."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    symbol: str = Field(..., description="Ticker symbol (e.g., AAPL)")
    info: InfoResponse = Field(..., description="Company information")
    quote: QuoteResponse = Field(..., description="Current stock quote")
    # Convenience top-level fields to support a compact response shape expected
    # by some clients/tests. These duplicate values available under `info` and
    # `quote` for easier consumption.
    current_price: float | None = Field(None, description="Current market price")
    currency: str | None = Field(None, description="Currency of the stock")
