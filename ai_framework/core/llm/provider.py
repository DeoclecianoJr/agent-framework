"""LLM provider factory and unified interface."""
import logging
from typing import Any, Dict, List, Optional, Union

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_community.callbacks import get_openai_callback

from ai_framework.core.config import settings
from ai_framework.core.resilience import retry_with_backoff, CircuitBreaker, CircuitBreakerError

from .base import BaseLLM
from .mock import MockLLM
from .ollama import OllamaLLM
from .gemini import GeminiLLM
from .utils import count_tokens, calculate_cost

logger = logging.getLogger(__name__)

# Global circuit breakers per provider
_circuit_breakers = {
    "openai": CircuitBreaker(name="openai", failure_threshold=5, recovery_timeout=60),
    "anthropic": CircuitBreaker(name="anthropic", failure_threshold=5, recovery_timeout=60),
    "ollama": CircuitBreaker(name="ollama", failure_threshold=5, recovery_timeout=60),
    "gemini": CircuitBreaker(name="gemini", failure_threshold=5, recovery_timeout=60),
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
        """Initialize LLM provider.
        
        Args:
            provider: Provider name (openai, anthropic, ollama, gemini, mock)
            model: Model name
            api_key: API key for the provider
            temperature: Sampling temperature
            **kwargs: Additional provider-specific parameters
        """
        self.provider = provider or settings.llm_provider
        self.model = model or settings.llm_model
        self.temperature = temperature
        self.api_key = api_key
        self.extra_params = kwargs
        self._client: Optional[BaseChatModel] = None

    def _get_client(self) -> Union[BaseChatModel, MockLLM, OllamaLLM, GeminiLLM]:
        """Lazy-load the underlying provider client.
        
        Returns:
            Configured LLM client instance
        """
        if self.provider == "mock":
            # Avoid duplicate response_text if provided in kwargs
            params = self.extra_params.copy()
            resp_text = params.pop("response_text", settings.mock_response)
            return MockLLM(response_text=resp_text, **params)
        
        if self.provider == "ollama":
            # Build Ollama config from settings and params
            base_url = self.extra_params.get("base_url", getattr(settings, "ollama_base_url", "http://localhost:11434"))
            timeout = self.extra_params.get("timeout", getattr(settings, "ollama_timeout", 60))
            num_ctx = self.extra_params.get("num_ctx", getattr(settings, "ollama_num_ctx", 2048))
            
            return OllamaLLM(
                model=self.model,
                base_url=base_url,
                temperature=self.temperature,
                num_ctx=num_ctx,
                timeout=timeout,
                **{k: v for k, v in self.extra_params.items() if k not in ["base_url", "timeout", "num_ctx"]}
            )
        
        if self.provider == "gemini":
            # Build Gemini config from settings and params
            api_key = self.api_key or settings.google_api_key
            temperature = self.extra_params.get("temperature", getattr(settings, "gemini_temperature", 0.7))
            max_output_tokens = self.extra_params.get("max_output_tokens", getattr(settings, "gemini_max_output_tokens", 2048))
            top_p = self.extra_params.get("top_p", getattr(settings, "gemini_top_p", 0.95))
            top_k = self.extra_params.get("top_k", getattr(settings, "gemini_top_k", 40))
            
            return GeminiLLM(
                api_key=api_key,
                model=self.model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                top_p=top_p,
                top_k=top_k,
                **{k: v for k, v in self.extra_params.items() if k not in ["temperature", "max_output_tokens", "top_p", "top_k"]}
            )
            
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
        """Send messages to the LLM and return a standardized response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
            
        Returns:
            Standardized response dict
        """
        client = self._get_client()
        
        # Extract tools if present in kwargs
        tools = kwargs.pop("tools", None)
        
        if isinstance(client, (MockLLM, OllamaLLM, GeminiLLM)):
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
                exceptions=(Exception,)  # LangChain exceptions
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
    """Factory function to get an LLM client.
    
    Args:
        provider: Provider name
        **kwargs: Additional parameters
        
    Returns:
        Configured LLM provider instance
    """
    return LLMProvider(provider=provider, **kwargs)
