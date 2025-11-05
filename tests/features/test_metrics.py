"""Tests for the /metrics endpoint"""

from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client.parser import text_string_to_metric_families

def test_metric_check_ok(client):
    """Test case for a successful metrics check."""
    response = client.get("/metrics")
    content_type = response.headers.get("Content-Type")
    assert response.status_code == 200
    assert content_type == CONTENT_TYPE_LATEST

    body = response.text
    families = {mf.name: mf for mf in text_string_to_metric_families(body)}
    assert "process_uptime_seconds" in families
    assert "build_info_info" in families

    assert any(True for _ in families["process_uptime_seconds"].samples)
    assert any(True for _ in families["build_info_info"].samples)

