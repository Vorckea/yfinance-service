"""News service: fetches news data for a given stock symbol."""

from app.clients.interface import YFinanceClientInterface
from app.features.news.models import NewsResponse
from app.utils.cache.news_cache import Key, NewsCache

from ...utils.logger import logger


async def fetch_news(
    symbol: str,
    count: int,
    tab: str,
    *,
    client: YFinanceClientInterface,
    news_cache: NewsCache | None = None,
) -> NewsResponse:
    """Fetch news for a given symbol.

    Args:
        symbol (str): The stock symbol to fetch news for.
        count (int): The number of news articles to fetch.
        tab (str): News type: news, press-releases, or all.
        client (YFinanceClientInterface): The YFinance client to use for fetching data.
        news_cache (NewsCache): The cache to use for storing news articles.
        Defaults to None.

    Returns:
        NewsResponse: The news response for the given symbol.

    """
    logger.info("news.fetch.start", extra={"symbol": symbol})

    if tab == "press-releases":
        tab = "press releases"

    if news_cache:
        cached = await news_cache.get(Key(symbol=symbol, news_type=tab), count)
        if cached is not None:
            logger.info("news.fetch.cache.hit", extra={"symbol": symbol, "tab": tab})
            return NewsResponse(news=cached)

    symbol = symbol.strip().upper()
    news = await client.get_news(symbol=symbol, count=count, tab=tab)
    result = NewsResponse.model_validate({"news": news})

    if news_cache:
        await news_cache.set(Key(symbol=symbol, news_type=tab), result.news)

    logger.info("news.fetch.success", extra={"symbol": symbol})
    return result
