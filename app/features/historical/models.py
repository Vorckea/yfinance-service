from datetime import date

from pydantic import BaseModel


class HistoricalPrice(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalResponse(BaseModel):
    symbol: str
    prices: list[HistoricalPrice]
