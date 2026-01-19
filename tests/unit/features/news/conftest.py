"""Fixtures for news feature tests."""

import copy

import pytest


@pytest.fixture(scope="function")
def news_payload_factory():
    """Return factory to create news payloads for testing."""
    base = {
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

    def _factory(count: int = 1, **overrides):
        base_copy = copy.deepcopy(base)
        base_copy.update(overrides)
        return [copy.deepcopy(base_copy) for _ in range(count)]

    return _factory
