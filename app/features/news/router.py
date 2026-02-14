"""News endpoint definitions."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.clients.interface import YFinanceClientInterface
from app.common.validation import SymbolParam
from app.dependencies import get_news_cache, get_settings, get_yfinance_client
from app.features.news.service import fetch_news
from app.utils.cache.news_cache import NewsCache

from .models import NewsResponse

router = APIRouter()
settings = get_settings()
TabAllowedValues = Literal["news", "press-releases", "all"]


@router.get(
    "/{symbol}",
    response_model=NewsResponse,
    summary="Get news for a symbol",
    description="Returns recent news articles related to the given ticker symbol.",
    operation_id="getNewsBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "news": [
                            {
                                "id": "ac1b7cd7-5c3a-41f6-84cc-9f27df508da0",
                                "content": {
                                    "id": "ac1b7cd7-5c3a-41f6-84cc-9f27df508da0",
                                    "contentType": "STORY",
                                    "title": (
                                        "'A broadening playbook': Wall Street sees stock market"
                                        "gains beyond tech",
                                    ),
                                    "description": "",
                                    "summary": (
                                        "Enthusiasm for artificial intelligence's prospects will"
                                        "continue to drive the market higher in 2026. The gains"
                                        "won't be limited to tech stocks, strategists say.",
                                    ),
                                    "pubDate": "2026-01-18T16:05:56Z",
                                    "displayTime": "2026-01-19T05:48:32Z",
                                    "isHosted": "true",
                                    "bypassModal": "false",
                                    "previewUrl": "null",
                                    "thumbnail": {
                                        "originalUrl": "https://s.yimg.com",
                                        "originalWidth": 4898,
                                        "originalHeight": 3265,
                                        "caption": "",
                                        "resolutions": [
                                            {
                                                "url": "https://s.yimg.com",
                                                "width": 4898,
                                                "height": 3265,
                                                "tag": "original",
                                            },
                                            {
                                                "url": "https://s.yimg.com",
                                                "width": 170,
                                                "height": 128,
                                                "tag": "170x128",
                                            },
                                        ],
                                    },
                                    "provider": {
                                        "displayName": "Yahoo Finance",
                                        "url": "http://finance.yahoo.com",
                                    },
                                    "canonicalUrl": {
                                        "url": "https://finance.yahoo.com",
                                        "site": "finance",
                                        "region": "US",
                                        "lang": "en-US",
                                    },
                                    "clickThroughUrl": {
                                        "url": "https://finance.yahoo.com",
                                        "site": "finance",
                                        "region": "US",
                                        "lang": "en-US",
                                    },
                                    "metadata": {"editorsPick": "true"},
                                    "finance": {
                                        "premiumFinance": {
                                            "isPremiumNews": "false",
                                            "isPremiumFreeNews": "false",
                                        }
                                    },
                                    "storyline": {
                                        "storylineItems": [
                                            {
                                                "content": {
                                                    "id": "23af3afd-ccaa-469f-8c5b-ef73004f7b62",
                                                    "contentType": "STORY",
                                                    "isHosted": "true",
                                                    "title": (
                                                        "Tesla's FSD, like almost everything else,"
                                                        "is becoming a subscription",
                                                    ),
                                                    "thumbnail": {
                                                        "originalUrl": "https://s.yimg.com",
                                                        "originalWidth": 6000,
                                                        "originalHeight": 4000,
                                                        "caption": "",
                                                        "resolutions": "null",
                                                    },
                                                    "provider": {
                                                        "displayName": "Yahoo Finance",
                                                        "sourceId": "yahoofinance.com",
                                                    },
                                                    "previewUrl": "null",
                                                    "providerContentUrl": "",
                                                    "canonicalUrl": {
                                                        "url": "https://finance.yahoo.com"
                                                    },
                                                    "clickThroughUrl": {
                                                        "url": "https://finance.yahoo.com"
                                                    },
                                                }
                                            },
                                            {
                                                "content": {
                                                    "id": "5d159d60-52a6-4eab-9d31-77227a87d912",
                                                    "contentType": "STORY",
                                                    "isHosted": "true",
                                                    "title": (
                                                        "The solar panel contracts that can kill"
                                                        "home sales",
                                                    ),
                                                    "thumbnail": {
                                                        "originalUrl": "https://s.yimg.com",
                                                        "originalWidth": 4616,
                                                        "originalHeight": 3077,
                                                        "caption": "",
                                                        "resolutions": "null",
                                                    },
                                                    "provider": {
                                                        "displayName": "Yahoo Finance",
                                                        "sourceId": "yahoofinance.com",
                                                    },
                                                    "previewUrl": "null",
                                                    "providerContentUrl": "",
                                                    "canonicalUrl": {
                                                        "url": "https://finance.yahoo.com"
                                                    },
                                                    "clickThroughUrl": {
                                                        "url": "https://finance.yahoo.com"
                                                    },
                                                }
                                            },
                                        ]
                                    },
                                },
                            }
                        ]
                    }
                }
            },
        },
        404: {"description": "No news data found for symbol"},
        422: {"description": "Validation error (invalid symbol or query parameters)"},
        499: {"description": "Request cancelled by client"},
        500: {"description": "Internal server error"},
        502: {"description": "Bad gateway"},
        503: {"description": "Upstream timeout"},
    },
)
async def get_news(
    symbol: SymbolParam,
    count: Annotated[
        int,
        Query(ge=1, le=settings.news_max_items, description="Number of news items to retrieve"),
    ] = 10,
    tab: Annotated[
        TabAllowedValues,
        Query(description="News type: news, press-releases, or all"),
    ] = "news",
    news_cache: NewsCache = Depends(get_news_cache),
    client: YFinanceClientInterface = Depends(get_yfinance_client),
) -> NewsResponse:
    """Get news for a given ticker symbol."""
    return await fetch_news(
        symbol=symbol,
        count=count,
        tab=tab,
        client=client,
        news_cache=news_cache,
    )
