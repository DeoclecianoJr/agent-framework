"""Tests for the configuration system (Task 2.5)."""

import os
import yaml
import pytest
from ai_framework.core.config import SDKSettings
from app.core.config import APISettings


def test_sdk_settings_defaults(monkeypatch):
    """Verify SDK default settings."""
    # Ensure no config file is loaded
    monkeypatch.setenv("AI_FRAMEWORK_CONFIG", "non_existent.yaml")
    settings = SDKSettings()
    assert settings.app_env == "dev"
    assert settings.debug is True
    assert settings.llm_provider == "mock"


def test_api_settings_defaults(monkeypatch):
    """Verify API default settings."""
    # Ensure no config file is loaded
    monkeypatch.setenv("AI_FRAMEWORK_CONFIG", "non_existent.yaml")
    settings = APISettings()
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.log_level == "INFO"


def test_env_override(monkeypatch):
    """Test environment variable overrides."""
    monkeypatch.setenv("AI_SDK_APP_ENV", "production")
    monkeypatch.setenv("AI_SDK_DEBUG", "false")
    monkeypatch.setenv("AI_APP_DATABASE_URL", "sqlite:///./prod.db")
    
    sdk_settings = SDKSettings()
    api_settings = APISettings()
    
    assert sdk_settings.app_env == "production"
    assert sdk_settings.debug is False
    assert api_settings.database_url == "sqlite:///./prod.db"


def test_yaml_load(monkeypatch, tmp_path):
    """Test YAML file loading."""
    config_file = tmp_path / "test_config.yaml"
    config_data = {
        "app_env": "staging",
        "llm_model": "gpt-3.5-turbo",
        "log_level": "ERROR"
    }
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    
    monkeypatch.setenv("AI_FRAMEWORK_CONFIG", str(config_file))
    
    # Reload settings
    sdk_settings = SDKSettings()
    api_settings = APISettings()
    
    assert sdk_settings.app_env == "staging"
    assert sdk_settings.llm_model == "gpt-3.5-turbo"
    assert api_settings.log_level == "ERROR"


def test_env_priority_over_yaml(monkeypatch, tmp_path):
    """Verify Env vars have priority over YAML."""
    config_file = tmp_path / "test_config.yaml"
    config_data = {"app_env": "yaml_env"}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)
    
    monkeypatch.setenv("AI_FRAMEWORK_CONFIG", str(config_file))
    monkeypatch.setenv("AI_SDK_APP_ENV", "env_priority")
    
    sdk_settings = SDKSettings()
    assert sdk_settings.app_env == "env_priority"
