"""Google Gemini LLM provider implementation."""
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

from .base import BaseLLM

logger = logging.getLogger(__name__)

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiLLM(BaseLLM):
    """Google Gemini LLM provider implementation using google-genai."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        top_p: float = 0.95,
        top_k: int = 40,
        timeout: int = 60,
        **kwargs: Any
    ):
        """Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key
            model: Gemini model name (e.g., 'gemini-2.5-flash')
            temperature: Sampling temperature (0.0-1.0)
            max_output_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google-genai not installed. Install with: pip install google-genai")
        
        from ai_framework.core.config import settings
        api_key = api_key or settings.google_api_key
        if not api_key:
            raise ValueError("Google API key not provided and GOOGLE_API_KEY not set")
            
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_name = model
            self.temperature = temperature
            self.max_output_tokens = max_output_tokens
            self.top_p = top_p
            self.top_k = top_k
            self.timeout = timeout
            self.extra_params = kwargs
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    def _count_tokens(self, text: str) -> int:
        """Count tokens using Gemini's tokenizer.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            if not text:
                return 0
            response = self.client.models.count_tokens(
                model=self.model_name,
                contents=text,
            )
            return getattr(response, "total_tokens", 0)
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}, using fallback")
            # Fallback: estimate 1 token ≈ 0.33 words
            words = len(text.split())
            return max(int(words / 0.33), 1)

    def _map_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Convert messages to Gemini format.
        
        Gemini expects role to be 'user' or 'model' (not 'assistant')
        
        Args:
            messages: Standard message format
            
        Returns:
            Gemini-formatted messages
        """
        gemini_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Map 'assistant' role to 'model' for Gemini
            if role == "assistant":
                role = "model"
            
            # Gemini doesn't support system messages in the same way
            # We'll prepend system messages to the first user message
            gemini_messages.append({"role": role, "parts": [content]})
        
        return gemini_messages

    async def chat(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False, 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generate chat completion using Gemini.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            **kwargs: Additional parameters
            
        Returns:
            Standardized response dict with content, usage, metadata
            
        Raises:
            Exception: If Gemini API request fails
        """
        try:
            gen_config = genai.types.GenerateContentConfig(
                temperature=kwargs.get("temperature", self.temperature),
                max_output_tokens=kwargs.get("max_output_tokens", self.max_output_tokens),
                top_p=kwargs.get("top_p", self.top_p),
                top_k=kwargs.get("top_k", self.top_k),
            )

            system_prompt = None
            conversation_messages = []

            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", "")
                else:
                    conversation_messages.append(msg)

            last_message = conversation_messages[-1].get("content", "") if conversation_messages else ""
            if system_prompt:
                last_message = f"{system_prompt}\n\n{last_message}"

            logger.debug(f"Gemini Request Content: {last_message}")

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=last_message,
                config=gen_config,
            )
            
            logger.debug(f"Gemini Response Content: {getattr(response, 'text', '')}")

            # Optimização: Usar metadados de uso da resposta se disponível
            usage_meta = getattr(response, "usage_metadata", None)
            if usage_meta:
                 prompt_tokens = getattr(usage_meta, "prompt_token_count", 0)
                 completion_tokens = getattr(usage_meta, "candidates_token_count", 0)
            else:
                 # Fallback para contagem manual (3 chamadas de API)
                 prompt_text = " ".join(m.get("content", "") for m in messages)
                 prompt_tokens = self._count_tokens(prompt_text)
                 completion_tokens = self._count_tokens(getattr(response, "text", ""))

            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost": self._calculate_cost(prompt_tokens, completion_tokens),
                "model": self.model_name
            }

            finish_reason = "UNKNOWN"
            candidates = getattr(response, "candidates", None)
            if candidates:
                first = candidates[0]
                finish_reason = getattr(getattr(first, "finish_reason", None), "name", "UNKNOWN")

            return {
                "content": getattr(response, "text", ""),
                "provider": "gemini",
                "model": self.model_name,
                "metadata": {
                    "model": self.model_name,
                    "provider": "gemini",
                    "finish_reason": finish_reason,
                    "usage": usage,
                },
                "usage": usage,
                "raw": response
            }

        except Exception as e:
            logger.error(f"Gemini request failed: {e}")
            raise

    async def chat_stream(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion from Gemini.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
            
        Yields:
            Stream chunks with content deltas
        """
        try:
            gen_config = genai.types.GenerateContentConfig(
                temperature=kwargs.get("temperature", self.temperature),
                max_output_tokens=kwargs.get("max_output_tokens", self.max_output_tokens),
                top_p=kwargs.get("top_p", self.top_p),
                top_k=kwargs.get("top_k", self.top_k),
            )

            system_prompt = None
            conversation_messages = []

            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", "")
                else:
                    conversation_messages.append(msg)

            last_message = conversation_messages[-1].get("content", "") if conversation_messages else ""
            if system_prompt:
                last_message = f"{system_prompt}\n\n{last_message}"

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=last_message,
                config=gen_config,
                stream=True,
            )

            for chunk in response:
                if getattr(chunk, "text", ""):
                    yield {
                        "content": chunk.text,
                        "provider": "gemini",
                        "model": self.model_name,
                        "done": False
                    }

            yield {
                "content": "",
                "provider": "gemini",
                "model": self.model_name,
                "done": True
            }

        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            raise

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on Gemini pricing.
        
        As of 2024, Gemini pricing:
        - gemini-pro: Free tier (1M tokens/day free)
        - gemini-pro-vision: $0.00125/1k input tokens + $0.00375/1k output tokens
        - gemini-1.5-pro: $1.25/1M input + $2.50/1M output tokens
        - gemini-1.5-flash: $0.075/1M input + $0.3/1M output tokens
        
        For MVP, we return 0 for free tier and implement premium pricing as needed.
        
        Args:
            prompt_tokens: Input token count
            completion_tokens: Output token count
            
        Returns:
            Estimated cost in USD
        """
        prices = {
            "gemini-pro": {"input": 0.0, "output": 0.0, "unit": "per_1k"},  # Free tier
            "gemini-pro-vision": {"input": 0.00125, "output": 0.00375, "unit": "per_1k"},
            "gemini-1.5-pro": {"input": 1.25, "output": 2.50, "unit": "per_1m"},
            "gemini-1.5-flash": {"input": 0.075, "output": 0.3, "unit": "per_1m"},
        }
        
        price_info = prices.get(self.model_name, {"input": 0.0, "output": 0.0, "unit": "per_1k"})
        
        if price_info.get("unit") == "per_1m":
            # Price per 1M tokens
            input_cost = (prompt_tokens / 1_000_000) * price_info["input"]
            output_cost = (completion_tokens / 1_000_000) * price_info["output"]
        else:
            # Price per 1k tokens (default)
            input_cost = (prompt_tokens / 1000) * price_info["input"]
            output_cost = (completion_tokens / 1000) * price_info["output"]
        
        return round(input_cost + output_cost, 6)

    def health_check(self) -> bool:
        """Verify Gemini API is accessible.
        
        Returns:
            True if Gemini API is working, False otherwise
        """
        try:
            response = self.client.models.count_tokens(model=self.model_name, contents="health check")
            return getattr(response, "total_tokens", 0) > 0
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """List available Gemini models.
        
        Returns:
            List of available Gemini model names
        """
        try:
            models = self.client.models.list()
            generative_models = [m.name.split('/')[-1] for m in models]
            return generative_models
        except Exception as e:
            logger.error(f"Failed to list Gemini models: {e}")
            return []
