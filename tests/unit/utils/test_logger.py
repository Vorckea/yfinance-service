"""Tests for logging utilities and request correlation context."""

import json
import logging

from app.settings import LogFormat, Settings
from app.utils.logger import JsonFormatter, RequestContextFilter, reset_correlation_id, set_correlation_id


def test_json_formatter_renders_extras():
    """JSON formatter should include standard fields and custom extras."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=12,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.correlation_id = "cid-123"
    record.symbol = "AAPL"

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["correlation_id"] == "cid-123"
    assert payload["symbol"] == "AAPL"


def test_request_context_filter_injects_correlation_id():
    """Request context filter should populate correlation ID on log records."""
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=28,
        msg="test",
        args=(),
        exc_info=None,
    )
    token = set_correlation_id("cid-456")

    try:
        assert RequestContextFilter().filter(record) is True
    finally:
        reset_correlation_id(token)

    assert record.correlation_id == "cid-456"
    assert record.cid == "cid-456"


def test_settings_support_json_log_format():
    """Settings should parse JSON log format from the environment."""
    settings = Settings(log_format="json")

    assert settings.log_format == LogFormat.JSON
