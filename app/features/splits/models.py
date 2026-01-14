from pydantic import BaseModel, Field

class StockSplit(BaseModel):
    date: str = Field(..., description="The date of the stock split")
    ratio: float = Field(..., description="The split ratio (e.g., 2.0 for a 2-for-1 split)")