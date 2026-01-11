"""Tests for historical data mapping."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from app.features.historical.models import HistoricalPrice
from app.features.historical.service import _map_history


def test_map_history_naive_index():
    """Test that naive datetime index is preserved in HistoricalPrice."""
    data = {
        "Open": [100.0],
        "High": [110.0],
        "Low": [95.0],
        "Close": [105.0],
        "Volume": [1000],
    }
    df = pd.DataFrame(data, index=[datetime(2024, 1, 1)])

    result = _map_history(df)

    assert isinstance(result, list)
    assert len(result) == 1
    item = result[0]
    assert isinstance(item, HistoricalPrice)
    assert item.volume == 1000


def test_map_history_timezone_aware():
    """Test that timezone-aware index results in date-only in HistoricalPrice."""
    index = [pd.Timestamp("2024-01-01 15:30", tz="UTC")]
    data = {
        "Open": [200.0],
        "High": [220.0],
        "Low": [190.0],
        "Close": [210.0],
        "Volume": [5000],
    }
    df = pd.DataFrame(data, index=index)

    result = _map_history(df)

    assert len(result) == 1
    # timezone-aware index → only date returned
    assert result[0].date.isoformat() == "2024-01-01"
    assert result[0].timestamp == datetime(2024, 1, 1, 15, 30, tzinfo=timezone.utc)


def test_map_history_nan_volume_becomes_none():
    """Test that NaN volume is converted to None in HistoricalPrice."""
    data = {
        "Open": [50.0, 60.0],
        "High": [55.0, 65.0],
        "Low": [45.0, 58.0],
        "Close": [52.0, 62.0],
        "Volume": [1000, np.nan],
    }
    index = [datetime(2024, 1, 2), datetime(2024, 1, 1)]
    df = pd.DataFrame(data, index=index)

    result = _map_history(df)

    # Check ordering: latest first
    assert result[0].date > result[1].date
    assert result[1].volume is None

def test_map_history_with_corrupt_prices():
    """_map_history should handle DataFrames with invalid price data."""
    # Create DataFrame with mixed valid/invalid prices
    df = pd.DataFrame({
        "Open": [100.0, "invalid", 102.0],
        "High": [101.0, 101.5, "bad"],
        "Low": [99.0, 99.5, 101.0],
        "Close": [100.5, 100.8, 101.5],
        "Volume": [1000, "corrupt", 1200]
    })
    df.index = pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"], tz="UTC")

    # Should not raise - returns prices with safe values
    prices = _map_history(df)
    assert len(prices) == 3

    # First row valid
    assert prices[0].open == 100.0
    assert prices[0].volume == 1000

    # Second row has corruption - fallback to 0.0 for prices, None for volume
    assert prices[1].open == 0.0
    assert prices[1].volume is None

    # Third row has corruption
    assert prices[2].high == 0.0
