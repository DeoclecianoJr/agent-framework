import pytest
from app.core.audit import log_audit_event
from app.core.models import AuditLog

def test_audit_logging_utility(sqlite_memory_db):
    """Test the low-level audit logging utility."""
    # Log an event
    entry = log_audit_event(
        sqlite_memory_db,
        "test_event",
        {"foo": "bar"},
        actor="tester"
    )
    
    assert entry.id is not None
    assert entry.event_type == "test_event"
    assert entry.event_data == {"foo": "bar"}
    assert entry.actor == "tester"
    
    # Query it back
    saved = sqlite_memory_db.query(AuditLog).first()
    assert saved.event_type == "test_event"
    assert saved.event_data["foo"] == "bar"

def test_audit_logging_endpoint(client, sqlite_memory_db):
    """Test the audit logs endpoint via admin API."""
    # Need to override dependency if client uses app with override
    # But client fixture likely overrides get_db
    
    # 1. Create API key (should trigger log)
    resp = client.post("/admin/api-keys", json={"name": "audit_test"})
    assert resp.status_code == 201
    data = resp.json()
    api_key = data["key"]
    
    # 2. Query audit logs
    logs_resp = client.get("/admin/audit-logs", headers={"X-API-Key": api_key})
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    
    # Verify we have at least one log
    assert len(logs) >= 1
    found = False
    for log in logs:
        if log["event_type"] == "create_api_key" and log["event_data"]["name"] == "audit_test":
            found = True
            assert log["actor"] == "admin"
            break
    
    assert found, "Did not find audit log for API key creation"

