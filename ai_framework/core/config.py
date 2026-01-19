"""SDK configuration system using Pydantic Settings."""

import os
from typing import Any, Dict, Optional, Type
import yaml
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """A settings source that loads variables from a YAML file."""

    def get_field_value(self, field, field_name):
        return None  # We use the __call__ method to load everything

    def __call__(self) -> Dict[str, Any]:
        config_path = os.getenv("AI_FRAMEWORK_CONFIG", "config.yaml")
        if not os.path.exists(config_path):
            return {}

        with open(config_path, "r") as f:
            try:
                return yaml.safe_load(f) or {}
            except yaml.YAMLError:
                return {}


class SDKSettings(BaseSettings):
    """Base settings for the AI Framework SDK."""

    model_config = SettingsConfigDict(
        env_prefix="AI_SDK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SDK Core Settings
    app_env: str = Field(default="dev")
    debug: bool = Field(default=True)
    
    # LLM Settings
    llm_provider: str = Field(default="mock")
    llm_model: str = Field(default="mock-model")
    mock_response: str = Field(default="mock-response")
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


# Global settings instance
settings = SDKSettings()
