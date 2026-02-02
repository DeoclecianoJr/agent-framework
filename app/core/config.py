"""Runtime API configuration extending SDK settings."""

from typing import Optional
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from ai_framework.core.config import SDKSettings


class APISettings(SDKSettings):
    """Configuration for the FastAPI Runtime API."""

    model_config = SettingsConfigDict(
        env_prefix="AI_SDK_",  # Use same prefix as SDK to avoid confusion
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database Settings
    database_url: str = Field(default="sqlite:///./test.db")
    
    # API Security
    secret_key: str = Field(default="dev-secret-key-change-me")
    api_key_header_name: str = "X-API-Key"
    
    # Logging
    log_level: str = "INFO"
    json_logs: bool = True


# Global API settings instance
api_settings = APISettings()
