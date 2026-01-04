from pydantic import BaseModel, Field

class StockSplit(BaseModel):
    date: str
    ratio: float

class SplitsRequest(BaseModel):
    # This regex ensures the symbol is 1-5 uppercase letters
    symbol: str = Field(..., pattern=r"^[A-Z]{1,5}$")