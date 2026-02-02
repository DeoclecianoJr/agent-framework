"""Base abstractions for LLM providers."""
import abc
from typing import Any, Dict, List


class BaseLLM(abc.ABC):
    """Base interface for LLM providers."""

    @abc.abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Send messages to the LLM and return a response payload."""
        pass


class LLMResponse:
    """Standardized response from any LLM provider."""
    
    def __init__(self, content: str, raw_response: Any, provider: str, model: str):
        self.content = content
        self.raw_response = raw_response
        self.provider = provider
        self.model = model
        self.metadata = getattr(raw_response, "response_metadata", {})
