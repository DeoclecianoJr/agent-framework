"""Ollama local LLM provider implementation."""
import json
import logging
from typing import Any, Dict, List, AsyncGenerator

import requests

from .base import BaseLLM

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """Ollama local LLM provider implementation."""

    def __init__(
        self,
        model: str = "phi3:mini",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        num_ctx: int = 2048,
        timeout: int = 60,
        **kwargs: Any
    ):
        """Initialize Ollama provider.
        
        Args:
            model: Ollama model name (e.g., 'phi3:mini', 'llama2')
            base_url: Ollama API base URL
            temperature: Sampling temperature (0.0-1.0)
            num_ctx: Context window size
            timeout: Request timeout in seconds
            **kwargs: Additional parameters
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.temperature = temperature
        self.num_ctx = num_ctx
        self.timeout = timeout
        self.extra_params = kwargs

    def _count_tokens(self, text: str) -> int:
        """Estimate tokens (Ollama doesn't provide exact counts).
        
        Uses word-based estimation: 1 token ≈ 0.75 words (English).
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        words = len(text.split())
        return max(int(words / 0.75), 1)

    def _map_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Convert messages to Ollama format.
        
        Args:
            messages: Standard message format
            
        Returns:
            Ollama-formatted messages
        """
        ollama_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            ollama_messages.append({"role": role, "content": content})
        return ollama_messages

    async def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs: Any) -> Dict[str, Any]:
        """Generate chat completion using Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response (not implemented in this method)
            **kwargs: Additional parameters
            
        Returns:
            Standardized response dict with content, usage, metadata
            
        Raises:
            Exception: If Ollama service is unavailable or request fails
        """
        url = f"{self.base_url}/api/chat"
        
        ollama_messages = self._map_messages(messages)
        
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_ctx": kwargs.get("num_ctx", self.num_ctx)
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            content = result.get("message", {}).get("content", "")
            
            # Estimate tokens
            prompt_text = " ".join(m.get("content", "") for m in messages)
            prompt_tokens = self._count_tokens(prompt_text)
            completion_tokens = self._count_tokens(content)
            
            # Build usage dict
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost": 0.0,  # Local inference is free
                "model": self.model
            }
            
            return {
                "content": content,
                "provider": "ollama",
                "model": self.model,
                "metadata": {
                    "model": self.model,
                    "provider": "ollama",
                    "ollama_model": result.get("model", self.model),
                    "created_at": result.get("created_at", ""),
                    "done": result.get("done", True),
                    "usage": usage,
                },
                "usage": usage,
                "raw": result
            }
            
        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timeout after {self.timeout}s")
            raise Exception(f"Ollama request timeout after {self.timeout}s")
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.base_url}")
            raise Exception(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise Exception(f"Ollama HTTP error: {e}")
        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    async def chat_stream(self, messages: List[Dict[str, str]], **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion from Ollama.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
            
        Yields:
            Stream chunks with content deltas
        """
        url = f"{self.base_url}/api/chat"
        
        ollama_messages = self._map_messages(messages)
        
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_ctx": kwargs.get("num_ctx", self.num_ctx)
            }
        }
        
        try:
            with requests.post(url, json=payload, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        
                        yield {
                            "content": content,
                            "provider": "ollama",
                            "model": self.model,
                            "done": chunk.get("done", False)
                        }
                        
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise

    def health_check(self) -> bool:
        """Verify Ollama service is running and model is available.
        
        Returns:
            True if Ollama is running and model is loaded, False otherwise
        """
        try:
            # Check service is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            # Verify model is available
            models_data = response.json()
            available_models = [m.get("name", "") for m in models_data.get("models", [])]
            
            # Check if our model is in the list (handle version tags)
            model_found = any(self.model in m or m.startswith(f"{self.model}:") for m in available_models)
            
            if not model_found:
                logger.warning(f"Model {self.model} not found. Available: {available_models}")
                
            return model_found
            
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """List available Ollama models.
        
        Returns:
            List of model names available locally
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            
            models_data = response.json()
            return [m.get("name", "") for m in models_data.get("models", [])]
            
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
