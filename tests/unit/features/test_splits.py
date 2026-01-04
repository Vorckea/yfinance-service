import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch

# --- 1. SUCCESSFUL CASE (CORRECT SYMBOL) ---
@pytest.mark.asyncio
async def test_read_splits_success(client):
    mock_data = pd.Series([2.0], index=pd.to_datetime(["2024-01-01"]))
    
    with patch("app.features.splits.service._client.get_splits", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_data
        response = client.get("/splits/AAPL")
        
        assert response.status_code == 200
        assert response.json()[0]["ratio"] == 2.0
        assert response.json()[0]["date"] == "2024-01-01"

# --- 2. WRONG SYMBOL (VALIDATION ERROR) ---
def test_read_splits_wrong_symbol(client):
    """Checks that symbols like '!!!' trigger a 422 Unprocessable Entity."""
    response = client.get("/splits/!!!")
    
    assert response.status_code == 422
    assert "detail" in response.json()

# --- 3. NO SPLITS FOUND ---
@pytest.mark.asyncio
async def test_read_splits_no_data(client):
    """Checks that a valid symbol with no splits returns an empty list []."""
    with patch("app.features.splits.service._client.get_splits", new_callable=AsyncMock) as mock_get:
        
        mock_get.return_value = pd.Series(dtype=float)
        
        response = client.get("/splits/GOOGL")
        
        assert response.status_code == 200
        assert response.json() == []

# --- 4. CACHE LOGIC ---
@pytest.mark.asyncio
async def test_splits_cache_logic():
    from app.features.splits.service import get_splits
    mock_data = pd.Series([2.0], index=pd.to_datetime(["2024-01-01"]))
    
    with patch("app.features.splits.service._client.get_splits", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_data
        # Explicitly testing multiple hits for the same symbol
        symbol = "TSLA"
        results = [await get_splits(symbol) for _ in range(3)]
        # Verify all calls returned the same data
        assert all(len(r) == 1 for r in results)
        assert all(r[0].ratio == 2.0 for r in results)
        # The client should only be called once; subsequent 2 calls come from cache
        assert mock_get.call_count == 1
        mock_get.assert_called_once_with(symbol)