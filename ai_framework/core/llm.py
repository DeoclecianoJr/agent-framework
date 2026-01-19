"""LLM abstraction layer using LangChain.

Provides a unified interface for multiple LLM providers (OpenAI, Anthropic, Mock).
"""
import logging
import abc
from typing import Any, Dict, List, Optional, Union

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_community.callbacks import get_openai_callback

from ai_framework.core.config import settings
from ai_framework.core.resilience import retry_with_backoff, CircuitBreaker, CircuitBreakerError

logger = logging.getLogger(__name__)

# Global circuit breakers per provider
_circuit_breakers = {
    "openai": CircuitBreaker(name="openai", failure_threshold=5, recovery_timeout=60),
    "anthropic": CircuitBreaker(name="anthropic", failure_threshold=5, recovery_timeout=60),
}

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

def count_tokens(text: Optional[str]) -> int:
    """Naive token counter placeholder (word-based).
    In the future, this should use tiktoken or provider-specific counters.
    """
    if not text:
        return 0
    return max(len(text.split()), 1)


def calculate_cost(tokens: Dict[str, int], provider: str, model: str) -> float:
    """Calculate approximate cost based on tokens and provider.
    
    Prices per 1k tokens (example prices).
    """
    prices = {
        "openai": {
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        },
        "anthropic": {
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
        }
    }
    
    if provider not in prices or model not in prices[provider]:
        return 0.0
        
    p = prices[provider][model]
    prompt_cost = (tokens.get("prompt_tokens", 0) / 1000) * p["prompt"]
    completion_cost = (tokens.get("completion_tokens", 0) / 1000) * p["completion"]
    
    return round(prompt_cost + completion_cost, 6)


class MockLLM(BaseLLM):
    """Mock implementation of a chat model for testing."""
    
    def __init__(self, response_text: str = "mock-response"):
        self.response_text = response_text
        
    async def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
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

class LLMProvider(BaseLLM):
    """Unified provider to interact with different LLM backends."""

    def __init__(
        self, 
        provider: Optional[str] = None, 
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs: Any
    ):
        self.provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        self.temperature = temperature
        self.api_key = api_key
        self.extra_params = kwargs
        self._client: Optional[BaseChatModel] = None

    def _get_client(self) -> Union[BaseChatModel, MockLLM]:
        """Lazy-load the underlying provider client."""
        if self.provider == "mock":
            return MockLLM(response_text=settings.mock_response, **self.extra_params)
            
        if self._client:
            return self._client
            
        if self.provider == "openai":
            api_key = self.api_key or settings.openai_api_key
            self._client = ChatOpenAI(
                model=self.model,
                api_key=api_key,
                temperature=self.temperature,
                **self.extra_params
            )
        elif self.provider == "anthropic":
            api_key = self.api_key or settings.anthropic_api_key
            self._client = ChatAnthropic(
                model=self.model,
                api_key=api_key,
                temperature=self.temperature,
                **self.extra_params
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
            
        return self._client

    async def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """Send messages to the LLM and return a standardized response."""
        client = self._get_client()
        
        # Extract tools if present in kwargs
        tools = kwargs.pop("tools", None)
        
        if isinstance(client, MockLLM):
            return await client.chat(messages, **kwargs)
            
        # Get circuit breaker for this provider
        cb = _circuit_breakers.get(self.provider)
        if cb and not cb.can_execute():
            raise CircuitBreakerError(f"Provider {self.provider} is currently unavailable (Circuit Breaker OPEN)")

        # Convert internal dict messages to LangChain messages
        lc_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        
        async def _invoke_llm():
            # Bind tools if provided
            local_client = client
            if tools:
                local_client = local_client.bind_tools(tools)
                
            if self.provider == "openai":
                with get_openai_callback() as cb_openai:
                    response = await local_client.ainvoke(lc_messages, **kwargs)
                    usage = {
                        "prompt_tokens": cb_openai.prompt_tokens,
                        "completion_tokens": cb_openai.completion_tokens,
                        "total_tokens": cb_openai.total_tokens,
                        "cost": cb_openai.total_cost
                    }
            else:
                response = await local_client.ainvoke(lc_messages, **kwargs)
                # Try to extract from metadata for others
                meta = getattr(response, "response_metadata", {})
                token_usage = meta.get("token_usage", {})
                usage = {
                    "prompt_tokens": token_usage.get("prompt_tokens", 0),
                    "completion_tokens": token_usage.get("completion_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                }
                # Fallback to naive count if 0
                if usage["total_tokens"] == 0:
                    usage["prompt_tokens"] = sum(count_tokens(m.content) for m in lc_messages)
                    usage["completion_tokens"] = count_tokens(response.content)
                    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
                
                usage["cost"] = calculate_cost(usage, self.provider, self.model)

            return {
                "content": response.content,
                "provider": self.provider,
                "model": self.model,
                "metadata": getattr(response, "response_metadata", {}),
                "usage": usage,
                "raw": response
            }

        try:
            # Wrap in retry
            result = await retry_with_backoff(
                _invoke_llm, 
                max_retries=settings.llm_max_retries if hasattr(settings, "llm_max_retries") else 3,
                initial_delay=1.0,
                exceptions=(Exception,) # LangChain exceptions
            )
            
            if cb:
                cb.record_success()
                
            return result
        except Exception as e:
            if cb:
                cb.record_failure()
            logger.error(f"Error calling {self.provider}: {e}")
            raise

def get_llm(provider: Optional[str] = None, **kwargs: Any) -> BaseLLM:
    """Factory function to get an LLM client."""
    return LLMProvider(provider=provider, **kwargs)
