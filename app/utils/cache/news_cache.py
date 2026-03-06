"""Specific cache for news data."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, NamedTuple

from app.monitoring.metrics import CACHE_HITS, CACHE_MISSES, CACHE_PUTS

from .ttl_in_memory import TTLCache

if TYPE_CHECKING:
    from app.features.news.models import NewsRow


class Key(NamedTuple):
    """Class that should be used as `NewsCache` key."""

    symbol: str
    news_type: str


class NewsCache:
    """A specific cache for news data.

    Combines an in-memory TTL cache with a simple dict for articles.
    The `_index_cache` maps a `Key` (symbol + news type) to a list of article UUIDs, and
    the `_articles_cache` maps article UUIDs to the actual article objects.
    This design allows for efficient retrieval of required amount of articles by symbol and news
    type, while also enabling old articles eviction.
    """

    def __init__(
        self,
        size: int,
        ttl: int,
        *,
        cache_name: str = "news_cache",
        resource: str = "news",
    ) -> None:
        """Initialize the cache."""
        self.size = size
        self.ttl = ttl
        self._cache_name = cache_name
        self._resource = resource
        self._lock = asyncio.Lock()
        self._articles_cache: dict[str, NewsRow] = {}
        self._index_cache: TTLCache[Key, list[str]] = TTLCache(
            size,
            ttl,
            cache_name="ttl_cache",
            resource="news",
        )
        # Labeled metric children for this cache instance
        self._hits = CACHE_HITS.labels(cache=self._cache_name, resource=self._resource)
        self._misses = CACHE_MISSES.labels(cache=self._cache_name, resource=self._resource)
        self._puts = CACHE_PUTS.labels(cache=self._cache_name, resource=self._resource)

    async def get(self, key: Key, count: int = 10) -> list[NewsRow] | None:
        """Get a article UUIDs by `Key`."""
        async with self._lock:
            if key.news_type == "all":
                news_key = Key(symbol=key.symbol, news_type="news")
                press_releases_key = Key(symbol=key.symbol, news_type="press releases")

                news_indexes = await self._index_cache.get(news_key) or []
                press_releases_indexes = await self._index_cache.get(press_releases_key) or []
                indexes = news_indexes + press_releases_indexes
            else:
                indexes = await self._index_cache.get(key) or []

            if len(indexes) == 0:
                self._misses.inc()
                return None

            articles: list[NewsRow] = []
            for index in indexes:
                article = self._articles_cache.get(index)
                if article is None:
                    self._articles_cache.pop(index, None)
                    continue

                articles.append(article)
                if len(articles) == count:
                    self._hits.inc()
                    return articles

            self._misses.inc()
            return None

    async def set(self, key: Key, articles: list[NewsRow]) -> None:
        """Add new articles to the cache and replace old ones by `Key`."""
        async with self._lock:
            if key.news_type == "all":
                # Don't save "all" news type since we join "news" and "press-releases"
                # when "all" is requested
                return

            await self._index_cache.set(key, [article.id for article in articles])
            for article in articles:
                self._articles_cache[article.id] = article
            self._puts.inc()

    async def delete(self, key: Key) -> None:
        """Delete articles from the cache by `Key`."""
        async with self._lock:
            indexes = await self._index_cache.get(key)
            await self._index_cache.delete(key)

            if indexes is None:
                return

            for article_id in indexes:
                if article_id in self._articles_cache:
                    self._articles_cache.pop(article_id, None)

    async def clear(self) -> None:
        """Clear the cache."""
        async with self._lock:
            await self._index_cache.clear()
            self._articles_cache.clear()
