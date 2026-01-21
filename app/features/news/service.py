"""News service: fetches news data for a given stock symbol."""

from app.clients.interface import YFinanceClientInterface
from app.features.news.models import NewsResponse

from ...utils.logger import logger


async def fetch_news(
    symbol: str,
    count: int,
    tab: str,
    client: YFinanceClientInterface,
) -> NewsResponse:
    """Fetch news for a given symbol.

    Args:
        symbol (str): The stock symbol to fetch news for.
        count (int): The number of news articles to fetch.
        tab (str): News type: news, press-releases, or all.
        client (YFinanceClientInterface): The YFinance client to use for fetching data.

    Returns:
        NewsResponse: The news response for the given symbol.

    """
    logger.info("news.fetch.start", extra={"symbol": symbol})

    if tab == "press-releases":
        tab = "press releases"

    symbol = symbol.strip().upper()
    news = await client.get_news(symbol=symbol, count=count, tab=tab)
    result = NewsResponse.model_validate({"news": news})

    logger.info("news.fetch.success", extra={"symbol": symbol})
    return result
