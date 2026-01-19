"""Tests for the /news endpoint."""

from typing import Any, Mapping

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.features.news.models import NewsResponse
from app.features.news.service import fetch_news

INVALID_SYMBOL = "!!!"
NOT_FOUND_SYMBOL = "ZZZZZZZZZZ"


@pytest.mark.asyncio
async def test_news(client, mock_yfinance_client, news_payload_factory):
    """Test news in normal case with expected fields and types."""
    count = 2
    mock_yfinance_client.get_news.return_value = news_payload_factory(count=count)

    response = client.get("/news/AAPL")
    assert response.status_code == 200
    news_response = NewsResponse.model_validate(response.json())

    assert isinstance(news_response, NewsResponse)
    assert len(news_response.news) == count
    for article in news_response.news:
        assert hasattr(article, "content")
        assert isinstance(article.content.title, str)
        assert isinstance(article.content.pub_date, str)

    assert news_response.news[0].content.content_type == "STORY"
    assert news_response.news[0].content.pub_date == "2025-12-31T17:56:38Z"
    assert news_response.news[0].content.is_hosted is True


@pytest.mark.asyncio
async def test_news_fetch_info_raises_on_none_from_client():
    """If the client returns None or a non-mapping, the service should raise an error.

    This guards against unexpected upstream responses and ensures the mapping step
    fails fast and loudly so the API layer can translate appropriately.
    """

    class BadClient:
        async def get_news(self, symbol: str, count: int, tab: str):
            return None

    with pytest.raises(ValidationError):
        await fetch_news("AAPL", 5, "news", BadClient())


@pytest.mark.asyncio
async def test_news_aliases_extra_fields_are_handled(news_payload_factory):
    """Ensure aliases and extra-field ignoring behave as expected."""
    payload = news_payload_factory(
        extraField="ignored",
    )

    class ClientMock:
        async def get_news(self, symbol: str, count: int, tab: str) -> list[Mapping[str, Any]]:
            return payload

    res = await fetch_news("AAPL", 1, "news", ClientMock())
    assert isinstance(res, NewsResponse)
    assert len(res.news) == 1
    article = res.news[0]
    assert hasattr(article, "content")
    assert article.content.content_type == "STORY"
    assert article.content.pub_date == "2025-12-31T17:56:38Z"
    assert not hasattr(article, "extraField")


@pytest.mark.parametrize("count", [-1, 0, 1, 5])
async def test_news_count_parameter(client, mock_yfinance_client, news_payload_factory, count):
    """Test news endpoint with various count parameters."""
    mock_yfinance_client.get_news.return_value = news_payload_factory(count=count)

    response = client.get(f"/news/AAPL?count={count}&tab=news")
    if count < 1:
        assert response.status_code == 422
    else:
        assert response.status_code == 200
        news_response = NewsResponse.model_validate(response.json())
        assert len(news_response.news) == count


@pytest.mark.parametrize("tab", ["news", "press-releases", "all", "invalid"])
async def test_news_tab_parameter(client, mock_yfinance_client, news_payload_factory, tab):
    """Test news endpoint with various tab parameters."""
    mock_yfinance_client.get_news.return_value = news_payload_factory()

    response = client.get(f"/news/AAPL?tab={tab}")
    if tab not in ["news", "press-releases", "all"]:
        assert response.status_code == 422
    else:
        assert response.status_code == 200


@pytest.mark.parametrize(
    "symbol, expected_status",
    [
        (INVALID_SYMBOL, 422),
        (NOT_FOUND_SYMBOL, 404),
    ],
)
async def test_news_errors(client, mock_yfinance_client, symbol, expected_status):
    """Test error handling for invalid and not-found symbols."""
    if expected_status == 404:
        mock_yfinance_client.get_news.side_effect = HTTPException(
            status_code=404,
            detail=f"No data for {symbol}",
        )

    response = client.get(f"/news/{symbol}?count=5&tab=news")
    assert response.status_code == expected_status

    body = response.json()
    if expected_status == 422:
        assert "detail" in body and isinstance(body["detail"], list)
        assert "type" in body["detail"][0]
        assert body["detail"][0]["type"] == "string_pattern_mismatch"
    elif expected_status == 404:
        assert "No data for" in str(body.get("detail", ""))
