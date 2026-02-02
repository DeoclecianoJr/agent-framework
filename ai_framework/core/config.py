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
    google_api_key: Optional[str] = None

    # Ollama Settings
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_timeout: int = Field(default=60)
    ollama_num_ctx: int = Field(default=2048)

    # Gemini Settings
    gemini_model: str = Field(default="gemini-pro")
    gemini_temperature: float = Field(default=0.7)
    gemini_max_output_tokens: int = Field(default=2048)
    gemini_top_p: float = Field(default=0.95)
    gemini_top_k: int = Field(default=40)

    # Resilience Settings
    llm_max_retries: int = Field(default=3)
    max_tool_iterations: int = Field(default=5)

    # Memory Settings
    memory_max_messages: int = Field(default=15)
    memory_summary_language: str = Field(default="português")

    # Guardrails Settings
    guardrails_enabled: bool = Field(default=True)
    default_allowed_themes: list[str] = Field(default_factory=list)

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
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


# Global settings instance
settings = SDKSettings()
