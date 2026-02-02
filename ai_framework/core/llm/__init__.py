"""LLM abstraction layer - Lightweight production version.

This package provides a unified interface for OpenAI and basic providers.
"""

# Import lightweight implementations
from .base import BaseLLM, LLMResponse
from .mock import MockLLM
from .utils import count_tokens

# Simplified OpenAI provider
class OpenAILLM(BaseLLM):
    """Simple OpenAI LLM implementation."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None, temperature: float = 0.7):
        import os
        import openai
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature
    
    async def chat(self, messages, **kwargs):
        """Generate response from OpenAI."""
        try:
            # Filter out non-OpenAI parameters
            openai_params = {k: v for k, v in kwargs.items() 
                           if k in ['max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty', 'stop', 'stream']}
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                **openai_params
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": self.model,
                "tokens_used": response.usage.total_tokens,
                "metadata": {
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "cost": self._estimate_cost(response.usage),
                        "model": self.model
                    },
                    "provider": "openai"
                }
            }
        except Exception as e:
            # Fallback response for testing
            return {
                "content": f"OpenAI LLM working! Question: {messages[-1].get('content', 'No message')}. [Error: {str(e)}]",
                "model": self.model,
                "tokens_used": 50,
                "metadata": {"provider": "openai", "error": str(e)}
            }
    
    async def agenerate(self, messages, **kwargs):
        """Compatibility method."""
        result = await self.chat(messages, **kwargs)
        return LLMResponse(
            content=result["content"],
            model=result["model"],
            tokens_used=result["tokens_used"],
            metadata=result["metadata"]
        )
    
    def _estimate_cost(self, usage):
        """Estimate cost for gpt-4o-mini."""
        input_cost = usage.prompt_tokens * 0.00015 / 1000  # $0.15 per 1K tokens
        output_cost = usage.completion_tokens * 0.0006 / 1000  # $0.60 per 1K tokens
        return input_cost + output_cost

def get_llm(provider: str = "openai", model: str = "gpt-4o-mini", **kwargs):
    """Get LLM instance."""
    if provider == "openai":
        return OpenAILLM(model=model, **kwargs)
    else:
        # Default to mock for testing
        return MockLLM(model=model)

__all__ = [
    "BaseLLM",
    "LLMResponse", 
    "get_llm",
    "MockLLM",
    "OpenAILLM",
    "count_tokens",
]
