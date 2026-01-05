import pytest
import pandas as pd
from unittest.mock import AsyncMock
from fastapi import HTTPException
from app.main import app  
from app.dependencies import get_yfinance_client, get_splits_cache

# --- 1. SUCCESSFUL CASE ---
@pytest.mark.asyncio
async def test_read_splits_success(client):
    mock_data = pd.Series([2.0], index=pd.to_datetime(["2024-01-01"]))
    
    mock_client = AsyncMock()
    mock_client.get_splits.return_value = mock_data
    
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None

    app.dependency_overrides[get_yfinance_client] = lambda: mock_client
    app.dependency_overrides[get_splits_cache] = lambda: mock_cache
    
    try:
        response = client.get("/splits/AAPL")
        assert response.status_code == 200
        assert response.json()[0]["ratio"] == 2.0
        assert response.json()[0]["date"] == "2024-01-01"
    finally:
        app.dependency_overrides.clear()

# --- 2. WRONG SYMBOL (VALIDATION ERROR) ---
def test_read_splits_wrong_symbol(client):
    response = client.get("/splits/!!!")
    assert response.status_code == 422

# --- 3. NO SPLITS FOUND ---
@pytest.mark.asyncio
async def test_read_splits_no_data(client):
    mock_client = AsyncMock()
    # Simulate client raising 404
    mock_client.get_splits.side_effect = HTTPException(status_code=404, detail="No data")
    
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None

    app.dependency_overrides[get_yfinance_client] = lambda: mock_client
    app.dependency_overrides[get_splits_cache] = lambda: mock_cache
    
    try:
        response = client.get("/splits/ZZZZ")
        assert response.status_code == 404
        assert response.json()["detail"] == "No data"
    finally:
        app.dependency_overrides.clear()

# --- 4. CACHE LOGIC ---
@pytest.mark.asyncio
async def test_splits_cache_logic():
    from app.features.splits.service import get_splits
    mock_data = pd.Series([2.0], index=pd.to_datetime(["2024-01-01"]))
    
    mock_client = AsyncMock()
    mock_client.get_splits.return_value = mock_data
    
    mock_cache = AsyncMock()
    mock_cache.get.side_effect = [None, [{"ratio": 2.0, "date": "2024-01-01"}]]
    
    symbol = "TSLA"
    await get_splits(symbol, mock_client, mock_cache)
    await get_splits(symbol, mock_client, mock_cache)
    
    assert mock_client.get_splits.call_count == 1
    assert mock_cache.set.call_count == 1