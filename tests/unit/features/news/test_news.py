"""Tests for the /news endpoint."""

from typing import Any, Mapping
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.clients.interface import YFinanceClientInterface
from app.features.news.models import NewsResponse
from app.features.news.service import fetch_news
from app.utils.cache.news_cache import Key, NewsCache

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
        await fetch_news("AAPL", 5, "news", client=BadClient())


@pytest.mark.asyncio
async def test_news_aliases_extra_fields_are_handled(news_payload_factory):
    """Ensure aliases and extra-field ignoring behave as expected."""
    payload = news_payload_factory(
        extraField="ignored",
    )

    class ClientMock:
        async def get_news(self, symbol: str, count: int, tab: str) -> list[Mapping[str, Any]]:
            return payload

    res = await fetch_news("AAPL", 1, "news", client=ClientMock())
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


@pytest.mark.asyncio
async def test_fetch_news_uses_cache_hit(news_payload_factory):
    """When a cached NewsResponse exists, `fetch_news` should return it and not call the client."""
    cache = NewsCache(size=10, ttl=60)
    cached = NewsResponse.model_validate({"news": news_payload_factory(count=4)})
    await cache.set(Key(symbol="AAPL", news_type="news"), cached.news)

    client = AsyncMock(spec_set=YFinanceClientInterface)
    result = await fetch_news("AAPL", 4, "news", client=client, news_cache=cache)
    assert result == cached
    client.get_news.assert_not_called()


@pytest.mark.asyncio
async def test_cache_set_on_miss(news_payload_factory):
    """When cache miss occurs, `fetch_news` should call the client and cache the result."""
    cache = AsyncMock(spec_set=NewsCache)
    cache.get.return_value = None
    client = AsyncMock(spec_set=YFinanceClientInterface)
    expected_value = news_payload_factory(count=3)
    client.get_news.return_value = expected_value

    result = await fetch_news("AAPL", 3, "news", client=client, news_cache=cache)
    cache.set.assert_awaited_once()
    assert NewsResponse.model_validate({"news": expected_value}) == result
    assert cache.set.call_args[0][0] == Key(symbol="AAPL", news_type="news")
    assert len(cache.set.call_args[0][1]) == 3


@pytest.mark.asyncio
async def test_cache_miss_when_fewer_articles_cached_than_requested(news_payload_factory):
    """When the cache has fewer articles than the requested count, it should be treated as a miss.

    NewsCache.get returns None when it cannot satisfy the full `count`.
    In that case fetch_news must fall through to the client, fetch fresh data,
    and update the cache with the new (larger) set of articles.
    """
    cache = NewsCache(size=10, ttl=60)

    # Pre-populate cache with only 2 articles
    small_payload = news_payload_factory(count=2)
    small_response = NewsResponse.model_validate({"news": small_payload})
    await cache.set(Key(symbol="AAPL", news_type="news"), small_response.news)

    # Client returns 5 articles
    large_payload = news_payload_factory(count=5)
    client = AsyncMock(spec_set=YFinanceClientInterface)
    client.get_news.return_value = large_payload

    result = await fetch_news("AAPL", 5, "news", client=client, news_cache=cache)

    # Client should have been called because the cache couldn't satisfy count=5
    client.get_news.assert_awaited_once()
    assert len(result.news) == 5


@pytest.mark.asyncio
async def test_cache_returns_subset_when_count_less_than_cached(news_payload_factory):
    """When more articles are cached than requested, only `count` articles are returned.

    If the cache holds 5 articles and the caller requests 3, NewsCache.get should
    return exactly 3, and the client should NOT be called at all.
    """
    cache = NewsCache(size=10, ttl=60)

    payload = news_payload_factory(count=5)
    full_response = NewsResponse.model_validate({"news": payload})
    await cache.set(Key(symbol="AAPL", news_type="news"), full_response.news)

    client = AsyncMock(spec_set=YFinanceClientInterface)
    result = await fetch_news("AAPL", 3, "news", client=client, news_cache=cache)

    client.get_news.assert_not_called()
    assert len(result.news) == 3


@pytest.mark.asyncio
async def test_cache_key_is_symbol_and_tab_specific(news_payload_factory):
    """Cache entries are keyed by (symbol, tab), so different tabs must not share results.

    Populating the cache for ("AAPL", "news") should not produce a hit when
    requesting ("AAPL", "press releases"). The client must be called for the
    uncached tab, and only that tab's result is returned.
    """
    cache = NewsCache(size=10, ttl=60)

    # Cache articles under the "news" tab
    news_payload = news_payload_factory(count=2)
    news_response = NewsResponse.model_validate({"news": news_payload})
    await cache.set(Key(symbol="AAPL", news_type="news"), news_response.news)

    # Request "press-releases" tab (normalised to "press releases" in the service)
    pr_payload = news_payload_factory(count=3)
    client = AsyncMock(spec_set=YFinanceClientInterface)
    client.get_news.return_value = pr_payload

    result = await fetch_news("AAPL", 3, "press-releases", client=client, news_cache=cache)

    # Client must be called because the "press releases" key was never cached
    client.get_news.assert_awaited_once()
    assert len(result.news) == 3


@pytest.mark.asyncio
async def test_cache_key_is_symbol_specific(news_payload_factory):
    """Cache entries for different symbols must be independent.

    Caching news for AAPL should not satisfy a request for MSFT.
    The client must be called for the uncached symbol.
    """
    cache = NewsCache(size=10, ttl=60)

    aapl_payload = news_payload_factory(count=2)
    aapl_response = NewsResponse.model_validate({"news": aapl_payload})
    await cache.set(Key(symbol="AAPL", news_type="news"), aapl_response.news)

    msft_payload = news_payload_factory(count=2)
    client = AsyncMock(spec_set=YFinanceClientInterface)
    client.get_news.return_value = msft_payload

    result = await fetch_news("MSFT", 2, "news", client=client, news_cache=cache)

    client.get_news.assert_awaited_once()
    assert len(result.news) == 2


@pytest.mark.asyncio
async def test_cache_all_merges_news_and_press_releases(news_payload_factory):
    """When tab is 'all', the cache merges articles from both 'news' and 'press releases' keys.

    If both ("AAPL", "news") and ("AAPL", "press releases") have been cached
    independently, a get with news_type='all' should return articles from both
    buckets concatenated (news first, then press releases), and the client
    should NOT be called.
    """
    cache = NewsCache(size=10, ttl=60)

    news_payload = news_payload_factory(count=2)
    news_articles = NewsResponse.model_validate({"news": news_payload}).news
    await cache.set(Key(symbol="AAPL", news_type="news"), news_articles)

    pr_payload = news_payload_factory(count=2)
    # Give press-release articles distinct IDs so they don't collide with news
    for i, article in enumerate(pr_payload):
        article["id"] = f"pr-{i}"
    pr_articles = NewsResponse.model_validate({"news": pr_payload}).news
    await cache.set(Key(symbol="AAPL", news_type="press releases"), pr_articles)

    client_mock = AsyncMock(spec_set=YFinanceClientInterface)
    result = await fetch_news("AAPL", 4, "all", client=client_mock, news_cache=cache)

    client_mock.get_news.assert_not_called()
    assert len(result.news) == 4
    # First two articles come from the "news" bucket, last two from "press releases"
    assert result.news[0].id == "0"
    assert result.news[1].id == "1"
    assert result.news[2].id == "pr-0"
    assert result.news[3].id == "pr-1"


@pytest.mark.asyncio
async def test_cache_all_miss_when_neither_bucket_cached(news_payload_factory):
    """When tab is 'all' and neither 'news' nor 'press releases' is cached, it's a cache miss.

    The merged index list is empty, so get returns None and the service must
    fall through to the client.
    """
    cache = NewsCache(size=10, ttl=60)

    payload = news_payload_factory(count=3)
    client_mock = AsyncMock(spec_set=YFinanceClientInterface)
    client_mock.get_news.return_value = payload

    result = await fetch_news("AAPL", 3, "all", client=client_mock, news_cache=cache)

    client_mock.get_news.assert_awaited_once()
    assert len(result.news) == 3


@pytest.mark.asyncio
async def test_cache_all_miss_when_only_news_cached_and_not_enough(news_payload_factory):
    """When only 'news' is cached and the merged total is fewer than the requested count.

    If the caller asks for 5 articles via tab='all' but only 2 are cached under
    'news' (and nothing under 'press releases'), the cache cannot satisfy the
    request and must return None — causing the client to be called.
    """
    cache = NewsCache(size=10, ttl=60)

    news_payload = news_payload_factory(count=2)
    news_articles = NewsResponse.model_validate({"news": news_payload}).news
    await cache.set(Key(symbol="AAPL", news_type="news"), news_articles)

    payload = news_payload_factory(count=5)
    client_mock = AsyncMock(spec_set=YFinanceClientInterface)
    client_mock.get_news.return_value = payload

    result = await fetch_news("AAPL", 5, "all", client=client_mock, news_cache=cache)

    client_mock.get_news.assert_awaited_once()
    assert len(result.news) == 5


@pytest.mark.parametrize("tab", ["news", "press releases"])
@pytest.mark.asyncio
async def test_cache_all_hit_with_only_one_bucket_when_count_satisfied(
    news_payload_factory,
    tab,
):
    """When only one bucket is cached (news or press releases) but has enough articles, it's a hit.

    Tab='all' merges 'news' + 'press releases'. If 'news' or 'press releases' alone has >= count
    articles and the other is empty, the cache can still fulfil the
    request without calling the client.
    """
    cache = NewsCache(size=10, ttl=60)

    payload = news_payload_factory(count=5)
    news_articles = NewsResponse.model_validate({"news": payload}).news
    await cache.set(Key(symbol="AAPL", news_type=tab), news_articles)

    client_mock = AsyncMock(spec_set=YFinanceClientInterface)

    if tab == "press releases":
        tab = "press-releases"
    result = await fetch_news("AAPL", 3, "all", client=client_mock, news_cache=cache)

    client_mock.get_news.assert_not_called()
    assert len(result.news) == 3
