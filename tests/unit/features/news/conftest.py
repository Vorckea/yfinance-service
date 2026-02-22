"""Fixtures for news feature tests."""

import copy
from typing import Any, Callable

import pytest


@pytest.fixture(scope="function")
def news_payload_factory() -> Callable[..., list[dict[str, Any]]]:
    """Return factory to create news payloads for testing."""
    base: dict[str, Any] = {
        "id": "aaab1111",
        "content": {
            "id": "c3618287-ab77-4707-9611-2472b0a47a20",
            "contentType": "STORY",
            "title": (
                "Warren Buffett is stepping down as Berkshire Hathaway CEO."
                "It's one of several big C-suite shake-ups in 2026."
            ),
            "description": "",
            "summary": "These CEOs are taking the helm in 2026.",
            "pubDate": "2025-12-31T17:56:38Z",
            "displayTime": "2026-01-03T14:07:21Z",
            "isHosted": True,
            "bypassModal": False,
            "previewUrl": None,
        },
    }

    def _factory(count: int = 1, **overrides: dict[str, Any]) -> list[dict[str, Any]]:
        base_copy = copy.deepcopy(base)
        base_copy.update(overrides)
        news: list[dict[str, Any]] = []
        for i in range(count):
            article = copy.deepcopy(base_copy)
            article["id"] = str(i)
            news.append(article)
        return news

    return _factory
