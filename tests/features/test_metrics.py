"""Tests for the /metrics endpoint"""

from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client.parser import text_string_to_metric_families

def test_metric_check_ok(client):
    """Test case for a successful metrics check."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST

    families = {mf.name: mf for mf in text_string_to_metric_families(response.text)}
    assert "process_uptime_seconds" in families
    assert "build_info_info" in families
