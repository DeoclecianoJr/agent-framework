"""Mock LLM provider for testing."""
from typing import Any, Dict, List

from .base import BaseLLM
from .utils import count_tokens


class MockLLM(BaseLLM):
    """Mock implementation of a chat model for testing."""
    
    def __init__(self, response_text: str = "mock-response"):
        """Initialize mock LLM.
        
        Args:
            response_text: Fixed response text to return
        """
        self.response_text = response_text
        self.model = "mock-model"
        
    async def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Return mock response.
        
        Args:
            messages: List of message dicts
            **kwargs: Additional parameters (ignored)
            
        Returns:
            Standardized mock response
        """
        prompt_tokens = sum(count_tokens(m.get("content", "")) for m in messages)
        completion_tokens = count_tokens(self.response_text)
        
        return {
            "content": self.response_text,
            "provider": "mock",
            "model": "mock-model",
            "metadata": {},
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost": 0.0
            }
        }
