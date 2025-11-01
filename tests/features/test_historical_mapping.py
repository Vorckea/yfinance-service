import pandas as pd
import numpy as np
from datetime import datetime
from app.features.historical.service import _map_history
from app.features.historical.models import HistoricalPrice


def test_map_history_naive_index():
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




def test_map_history_nan_volume_becomes_none():
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

