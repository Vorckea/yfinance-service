import yfinance as yf
from .models import StockSplit

def get_splits(symbol: str) -> list[StockSplit]:
    ticker = yf.Ticker(symbol)
    splits_series = ticker.splits
    
    if splits_series is None or len(splits_series) == 0:
        return []

    return [
        StockSplit(date=str(date), ratio=float(ratio)) 
        for date, ratio in splits_series.items()
    ]