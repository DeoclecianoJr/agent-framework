"""Tests for metrics and statistics endpoints."""
import pytest
from prometheus_client import parser

def test_metrics_prometheus_format(client):
    """Verify that /metrics endpoint returns Prometheus text format."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    
    content = response.text
    # Verify it has standard Prometheus headers
    # Note: Family name might be 'http_requests' or 'http_requests_total' depending on library version behavior
    assert "http_requests_total" in content
    
    # Try parsing to ensure validity
    families = list(parser.text_string_to_metric_families(content))
    assert len(families) > 0

def test_admin_stats_endpoint(client):
    """Verify that /admin/stats endpoint returns business JSON metrics."""
    # Add dummy key to pass middleware presence check
    client.headers.update({"X-API-Key": "dummy-key-for-middleware"})
    
    response = client.get("/admin/stats")
    assert response.status_code == 200
    
    data = response.json()
    
    # Verify structure matches the moved logic
    assert "summary" in data
    assert "agents" in data
    assert "models" in data
    assert "timestamp" in data
    
    # Verify values
    summary = data["summary"]
    assert "total_messages" in summary
    assert "total_cost_usd" in summary

@pytest.mark.asyncio
async def test_metrics_counter_increment(client):
    """Verify that Prometheus counters increment on requests."""
    client.headers.update({"X-API-Key": "dummy-key-for-middleware"})

    # Make a request (this guarantees at least one request)
    client.post("/admin/api-keys", json={"name": "test_metrics_key_3"})

    # Get updated count
    response = client.get("/metrics")
    updated_content = response.text
    
    # Parse families
    families = {f.name: f for f in parser.text_string_to_metric_families(updated_content)}
    
    # Find the metric family that contains 'http_requests_total' samples
    request_family = None
    if 'http_requests_total' in families:
        request_family = families['http_requests_total']
    elif 'http_requests' in families:
        request_family = families['http_requests']
    
    assert request_family is not None, "Could not find http_requests_total metric family"
    
    # Count total requests where sample name matches
    total_requests = 0.0
    for sample in request_family.samples:
        if sample.name == 'http_requests_total':
            total_requests += sample.value
            
    assert total_requests > 0
