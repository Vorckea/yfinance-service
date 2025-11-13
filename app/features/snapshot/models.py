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
