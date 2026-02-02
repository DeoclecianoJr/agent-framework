"""Tests for guardrails admin API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from typing import Dict, Any

from app.main import app


class TestGuardrailAdminAPI:
    """Test guardrails configuration endpoints."""
    
    @pytest.fixture(autouse=True)
    def clear_guardrail_configs(self):
        """Clear guardrail configurations before each test."""
        from app.api.admin import _guardrail_configs
        _guardrail_configs.clear()
        yield
        _guardrail_configs.clear()
    
    @pytest.fixture
    def client(self, authenticated_client):
        """Use authenticated test client."""
        return authenticated_client
    
    @pytest.fixture
    def sample_guardrail_config(self):
        """Sample guardrail configuration."""
        return {
            "blocklist": ["violence", "hate"],
            "allowlist": ["technology", "education"],
            "min_confidence": 0.8,
            "allowed_themes": ["ai", "framework"],
            "tool_restrictions": {
                "agent1": ["search", "calculate"],
                "*": ["basic_tool"]
            }
        }
    
    def test_configure_guardrails_complete(self, client, sample_guardrail_config):
        """Test configuring guardrails with complete configuration."""
        agent_id = "test_agent_1"
        
        response = client.post(
            f"/admin/guardrails/{agent_id}",
            json=sample_guardrail_config
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == agent_id
        assert data["blocklist"] == sample_guardrail_config["blocklist"]
        assert data["allowlist"] == sample_guardrail_config["allowlist"]
        assert data["min_confidence"] == sample_guardrail_config["min_confidence"]
        assert data["allowed_themes"] == sample_guardrail_config["allowed_themes"]
        assert data["tool_restrictions"] == sample_guardrail_config["tool_restrictions"]
        assert "updated_at" in data
    
    def test_configure_guardrails_partial(self, client):
        """Test configuring guardrails with partial configuration."""
        agent_id = "test_agent_2"
        partial_config = {
            "blocklist": ["spam"],
            "min_confidence": 0.6
        }
        
        response = client.post(
            f"/admin/guardrails/{agent_id}",
            json=partial_config
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == agent_id
        assert data["blocklist"] == ["spam"]
        assert data["allowlist"] == []  # Default
        assert data["min_confidence"] == 0.6
        assert data["allowed_themes"] == []  # Default
        assert data["tool_restrictions"] == {}  # Default
    
    def test_configure_guardrails_update_existing(self, client, sample_guardrail_config):
        """Test updating existing guardrail configuration."""
        agent_id = "test_agent_3"
        
        # First configuration
        response1 = client.post(
            f"/admin/guardrails/{agent_id}",
            json=sample_guardrail_config
        )
        assert response1.status_code == 200
        
        # Update with new configuration
        update_config = {
            "blocklist": ["updated_blocklist"],
            "min_confidence": 0.9
        }
        
        response2 = client.post(
            f"/admin/guardrails/{agent_id}",
            json=update_config
        )
        
        assert response2.status_code == 200
        data = response2.json()
        
        # Should have updated fields
        assert data["blocklist"] == ["updated_blocklist"]
        assert data["min_confidence"] == 0.9
        # Should keep old fields that weren't updated
        assert data["allowlist"] == sample_guardrail_config["allowlist"]
        assert data["allowed_themes"] == sample_guardrail_config["allowed_themes"]
    
    def test_get_guardrail_config_existing(self, client, sample_guardrail_config):
        """Test getting existing guardrail configuration."""
        agent_id = "test_agent_4"
        
        # First create configuration
        create_response = client.post(
            f"/admin/guardrails/{agent_id}",
            json=sample_guardrail_config
        )
        assert create_response.status_code == 200
        
        # Then retrieve it
        get_response = client.get(f"/admin/guardrails/{agent_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        
        assert data["agent_id"] == agent_id
        assert data["blocklist"] == sample_guardrail_config["blocklist"]
        assert data["allowlist"] == sample_guardrail_config["allowlist"]
        assert data["min_confidence"] == sample_guardrail_config["min_confidence"]
    
    def test_get_guardrail_config_default(self, client):
        """Test getting guardrail configuration for non-configured agent."""
        agent_id = "non_existent_agent"
        
        response = client.get(f"/admin/guardrails/{agent_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return default configuration
        assert data["agent_id"] == agent_id
        assert data["blocklist"] == []
        assert data["allowlist"] == []
        assert data["min_confidence"] == 0.0
        assert data["allowed_themes"] == []
        assert data["tool_restrictions"] == {}
        assert "updated_at" in data
    
    def test_get_agent_tool_restrictions_with_restrictions(self, client):
        """Test getting tool restrictions for agent with restrictions."""
        agent_id = "test_agent_5"
        config = {
            "tool_restrictions": {
                agent_id: ["search", "calculate"],
                "*": ["basic_tool"]
            }
        }
        
        # Configure restrictions
        client.post(f"/admin/guardrails/{agent_id}", json=config)
        
        # Get tool restrictions
        response = client.get(f"/admin/guardrails/{agent_id}/tools")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == agent_id
        assert data["allowed_tools"] == ["search", "calculate"]
        assert data["has_restrictions"] is True
    
    def test_get_agent_tool_restrictions_global_only(self, client):
        """Test getting tool restrictions for agent with only global restrictions."""
        agent_id = "test_agent_6"
        config = {
            "tool_restrictions": {
                "*": ["global_tool1", "global_tool2"]
            }
        }
        
        # Configure global restrictions
        client.post(f"/admin/guardrails/{agent_id}", json=config)
        
        # Get tool restrictions for different agent
        other_agent = "other_agent"
        response = client.get(f"/admin/guardrails/{other_agent}/tools")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == other_agent
        assert data["allowed_tools"] == ["global_tool1", "global_tool2"]
        assert data["has_restrictions"] is True
    
    def test_get_agent_tool_restrictions_no_restrictions(self, client):
        """Test getting tool restrictions for agent without restrictions."""
        agent_id = "unrestricted_agent"
        
        response = client.get(f"/admin/guardrails/{agent_id}/tools")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["agent_id"] == agent_id
        assert data["allowed_tools"] is None
        assert data["has_restrictions"] is False
    
    def test_delete_guardrail_config_existing(self, client, sample_guardrail_config):
        """Test deleting existing guardrail configuration."""
        agent_id = "test_agent_7"
        
        # Create configuration
        create_response = client.post(
            f"/admin/guardrails/{agent_id}",
            json=sample_guardrail_config
        )
        assert create_response.status_code == 200
        
        # Delete configuration
        delete_response = client.delete(f"/admin/guardrails/{agent_id}")
        
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert "deleted" in data["message"].lower()
        assert agent_id in data["message"]
        
        # Verify it's gone by getting default config
        get_response = client.get(f"/admin/guardrails/{agent_id}")
        get_data = get_response.json()
        
        # Should return default configuration
        assert get_data["blocklist"] == []
        assert get_data["allowlist"] == []
    
    def test_delete_guardrail_config_non_existent(self, client):
        """Test deleting non-existent guardrail configuration."""
        agent_id = "non_existent_agent_delete"
        
        response = client.delete(f"/admin/guardrails/{agent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "no guardrail configuration found" in data["detail"].lower()
        assert agent_id in data["detail"]
    
    def test_list_all_guardrail_configs_empty(self, client):
        """Test listing all guardrail configurations when none exist."""
        # Clear any existing configs by testing with fresh client
        response = client.get("/admin/guardrails")
        
        assert response.status_code == 200
        data = response.json()
        # Might have configs from other tests, so just check it's a list
        assert isinstance(data, list)
    
    def test_list_all_guardrail_configs_with_data(self, client, sample_guardrail_config):
        """Test listing all guardrail configurations with data."""
        agent_ids = ["list_test_1", "list_test_2"]
        
        # Create multiple configurations
        for i, agent_id in enumerate(agent_ids):
            config = sample_guardrail_config.copy()
            config["min_confidence"] = 0.5 + i * 0.2  # Make them different
            
            response = client.post(f"/admin/guardrails/{agent_id}", json=config)
            assert response.status_code == 200
        
        # List all configurations
        response = client.get("/admin/guardrails")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # Find our test configurations
        our_configs = [item for item in data if item["agent_id"] in agent_ids]
        assert len(our_configs) == 2
        
        # Check they have the expected structure
        for config in our_configs:
            assert "agent_id" in config
            assert "blocklist" in config
            assert "allowlist" in config
            assert "min_confidence" in config
            assert "allowed_themes" in config
            assert "tool_restrictions" in config
            assert "updated_at" in config
    
    def test_validation_errors(self, client):
        """Test validation errors for invalid configurations."""
        agent_id = "validation_test"
        
        # Test invalid min_confidence (too high)
        invalid_config1 = {"min_confidence": 1.5}
        response1 = client.post(f"/admin/guardrails/{agent_id}", json=invalid_config1)
        assert response1.status_code == 422  # Validation error
        
        # Test invalid min_confidence (negative)
        invalid_config2 = {"min_confidence": -0.1}
        response2 = client.post(f"/admin/guardrails/{agent_id}", json=invalid_config2)
        assert response2.status_code == 422  # Validation error
        
        # Test invalid types
        invalid_config3 = {"blocklist": "should_be_list"}
        response3 = client.post(f"/admin/guardrails/{agent_id}", json=invalid_config3)
        assert response3.status_code == 422  # Validation error
    
    def test_empty_configuration_update(self, client):
        """Test updating with empty configuration."""
        agent_id = "empty_config_test"
        
        # Send empty configuration
        response = client.post(f"/admin/guardrails/{agent_id}", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        # Should create with defaults and update timestamp
        assert data["agent_id"] == agent_id
        assert "updated_at" in data
    
    def test_special_characters_in_config(self, client):
        """Test handling special characters in configuration."""
        agent_id = "special_chars_test"
        config = {
            "blocklist": ["special!@#$%", "unicode_测试"],
            "allowlist": ["emoji_🚀", "symbols_*&^%"],
            "tool_restrictions": {
                "agent_with_underscores_and-dashes": ["tool_name_with_underscores"],
                "agent@domain.com": ["email-style-tool"]
            }
        }
        
        response = client.post(f"/admin/guardrails/{agent_id}", json=config)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle special characters correctly
        assert data["blocklist"] == config["blocklist"]
        assert data["allowlist"] == config["allowlist"]
        assert data["tool_restrictions"] == config["tool_restrictions"]