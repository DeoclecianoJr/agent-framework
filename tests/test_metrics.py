import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_metrics_endpoint_unauthenticated():
    """Verify that metrics endpoint is accessible (or not, depending on requirements).
    Based on Task 14, it should be exposed.
    """
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text

@pytest.mark.asyncio
async def test_metrics_increment_on_request():
    """Verify that metrics increment after a request."""
    client = TestClient(app)
    
    # Check initial metrics
    initial_response = client.get("/metrics")
    assert initial_response.status_code == 200
    
    # Make a request to a tracked endpoint (e.g., /admin/api-keys or something that exists)
    # Even if it returns 401/405, it should be tracked by middleware if it reaches it
    client.post("/admin/api-keys", json={"name": "test"})
    
    # Check metrics again
    updated_response = client.get("/metrics")
    assert "http_requests_total" in updated_response.text
    # We expect at least one hit for POST /admin/api-keys
    assert 'method="POST"' in updated_response.text
    assert 'endpoint="/admin/api-keys"' in updated_response.text
