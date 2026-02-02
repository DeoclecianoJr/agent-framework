"""
Simplified LLM provider for production testing.
Removes heavy LangChain dependencies.
"""

from typing import Dict, Any, Optional, List
import json
import logging
import os


class BaseLLM:
    """Base LLM interface"""
    
    def __init__(self, model: str = "mock", **kwargs):
        self.model = model
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Chat completion interface"""
        raise NotImplementedError
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count"""
        return len(text.split()) * 1.3  # Rough estimation


class MockLLM(BaseLLM):
    """Mock LLM for testing"""
    
    def __init__(self, **kwargs):
        super().__init__(model="mock")
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Return a mock response"""
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
        
        response = f"Mock LLM response to: '{user_message}'. This is a test response from the production setup."
        
        return {
            "content": response,
            "model": self.model,
            "tokens_used": self.count_tokens(response),
            "metadata": {
                "provider": "mock",
                "mock_response": True
            }
        }


class LLMProvider:
    """Simplified LLM provider factory"""
    
    _instances = {}
    
    @classmethod
    def get_llm(cls, provider: str = None, **kwargs) -> BaseLLM:
        """Get LLM instance"""
        provider = provider or os.getenv("AI_SDK_LLM_PROVIDER", "mock")
        
        if provider not in cls._instances:
            if provider == "mock" or provider == "local":
                cls._instances[provider] = MockLLM(**kwargs)
            else:
                # For production, default to mock if other providers not available
                logging.warning(f"Provider {provider} not available, using mock")
                cls._instances[provider] = MockLLM(**kwargs)
        
        return cls._instances[provider]


def get_llm(provider: str = None, **kwargs) -> BaseLLM:
    """Get configured LLM instance"""
    return LLMProvider.get_llm(provider, **kwargs)


def count_tokens(text: str) -> int:
    """Count tokens in text"""
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback estimation
        return len(text.split()) * 1.3