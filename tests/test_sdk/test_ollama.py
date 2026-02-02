"""Tests for Ollama LLM provider."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from ai_framework.core.llm import OllamaLLM, LLMProvider, get_llm
import requests


class TestOllamaLLMUnit:
    """Unit tests for OllamaLLM class."""

    def test_ollama_initialization_defaults(self):
        """Test Ollama provider initializes with default values."""
        provider = OllamaLLM()
        assert provider.model == "phi3:mini"
        assert provider.base_url == "http://localhost:11434"
        assert provider.temperature == 0.7
        assert provider.num_ctx == 2048
        assert provider.timeout == 60

    def test_ollama_initialization_custom(self):
        """Test Ollama provider initializes with custom values."""
        provider = OllamaLLM(
            model="llama2",
            base_url="http://custom:8080",
            temperature=0.5,
            num_ctx=4096,
            timeout=120
        )
        assert provider.model == "llama2"
        assert provider.base_url == "http://custom:8080"
        assert provider.temperature == 0.5
        assert provider.num_ctx == 4096
        assert provider.timeout == 120

    def test_ollama_count_tokens(self):
        """Test token counting estimation."""
        provider = OllamaLLM()
        
        # Test basic text
        tokens = provider._count_tokens("Hello world")
        assert tokens > 0
        assert tokens < 10  # Should be around 2-3 tokens
        
        # Test longer text
        long_text = " ".join(["word"] * 100)
        tokens_long = provider._count_tokens(long_text)
        assert tokens_long > tokens
        assert tokens_long > 100  # ~133 tokens for 100 words
        
        # Test empty text
        assert provider._count_tokens("") == 0
        assert provider._count_tokens(None) == 0

    def test_ollama_map_messages(self):
        """Test message format conversion."""
        provider = OllamaLLM()
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        mapped = provider._map_messages(messages)
        assert len(mapped) == 3
        assert mapped[0] == {"role": "system", "content": "You are helpful"}
        assert mapped[1] == {"role": "user", "content": "Hello"}
        assert mapped[2] == {"role": "assistant", "content": "Hi there"}

    @pytest.mark.asyncio
    async def test_ollama_chat_success(self):
        """Test chat completion with mocked Ollama API."""
        provider = OllamaLLM(model="phi3:mini")
        
        # Mock response from Ollama
        mock_response = {
            "model": "phi3:mini",
            "created_at": "2026-01-21T12:00:00Z",
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you?"
            },
            "done": True
        }
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = Mock()
            
            messages = [{"role": "user", "content": "Hi"}]
            result = await provider.chat(messages)
            
            # Verify response structure
            assert result["content"] == "Hello! How can I help you?"
            assert result["provider"] == "ollama"
            assert result["model"] == "phi3:mini"
            assert result["usage"]["prompt_tokens"] > 0
            assert result["usage"]["completion_tokens"] > 0
            assert result["usage"]["total_tokens"] > 0
            assert result["usage"]["cost"] == 0.0
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "http://localhost:11434/api/chat" in call_args[0]
            payload = call_args[1]["json"]
            assert payload["model"] == "phi3:mini"
            assert payload["stream"] is False
            assert payload["messages"] == [{"role": "user", "content": "Hi"}]

    @pytest.mark.asyncio
    async def test_ollama_chat_custom_params(self):
        """Test chat with custom temperature and context."""
        provider = OllamaLLM(model="phi3:mini", temperature=0.3, num_ctx=4096)
        
        mock_response = {
            "model": "phi3:mini",
            "message": {"role": "assistant", "content": "Response"},
            "done": True
        }
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = Mock()
            
            messages = [{"role": "user", "content": "Test"}]
            await provider.chat(messages, temperature=0.9)
            
            payload = mock_post.call_args[1]["json"]
            assert payload["options"]["temperature"] == 0.9  # Override
            assert payload["options"]["num_ctx"] == 4096

    @pytest.mark.asyncio
    async def test_ollama_connection_error(self):
        """Test error handling when Ollama is unavailable."""
        provider = OllamaLLM(base_url="http://localhost:99999")
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError()
            
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(Exception, match="Cannot connect to Ollama"):
                await provider.chat(messages)

    @pytest.mark.asyncio
    async def test_ollama_timeout_error(self):
        """Test error handling on timeout."""
        provider = OllamaLLM(timeout=5)
        
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(Exception, match="timeout"):
                await provider.chat(messages)

    @pytest.mark.asyncio
    async def test_ollama_http_error(self):
        """Test error handling on HTTP errors."""
        provider = OllamaLLM()
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
            mock_post.return_value = mock_response
            
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(Exception, match="HTTP error"):
                await provider.chat(messages)

    @pytest.mark.asyncio
    async def test_ollama_streaming(self):
        """Test streaming responses from Ollama."""
        provider = OllamaLLM(model="phi3:mini")
        
        # Mock streaming response
        mock_chunks = [
            b'{"message":{"content":"Hello"},"done":false}\n',
            b'{"message":{"content":" world"},"done":false}\n',
            b'{"message":{"content":"!"},"done":true}\n'
        ]
        
        with patch('requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=False)
            mock_response.raise_for_status = Mock()
            mock_response.iter_lines.return_value = mock_chunks
            mock_post.return_value = mock_response
            
            messages = [{"role": "user", "content": "Hi"}]
            chunks = []
            
            async for chunk in provider.chat_stream(messages):
                chunks.append(chunk)
            
            assert len(chunks) == 3
            assert chunks[0]["content"] == "Hello"
            assert chunks[1]["content"] == " world"
            assert chunks[2]["content"] == "!"
            assert chunks[2]["done"] is True
            
            # Verify streaming was enabled
            payload = mock_post.call_args[1]["json"]
            assert payload["stream"] is True

    def test_ollama_health_check_success(self):
        """Test health check when Ollama is running."""
        provider = OllamaLLM(model="phi3:mini")
        
        mock_response = {
            "models": [
                {"name": "phi3:mini"},
                {"name": "llama2:7b"}
            ]
        }
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = Mock()
            
            result = provider.health_check()
            assert result is True
            
            mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=5)

    def test_ollama_health_check_model_not_found(self):
        """Test health check when model is not available."""
        provider = OllamaLLM(model="nonexistent")
        
        mock_response = {
            "models": [
                {"name": "phi3:mini"},
                {"name": "llama2:7b"}
            ]
        }
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = Mock()
            
            result = provider.health_check()
            assert result is False

    def test_ollama_health_check_service_down(self):
        """Test health check when Ollama service is down."""
        provider = OllamaLLM()
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()
            
            result = provider.health_check()
            assert result is False

    def test_ollama_list_models_success(self):
        """Test listing available models."""
        provider = OllamaLLM()
        
        mock_response = {
            "models": [
                {"name": "phi3:mini"},
                {"name": "llama2:7b"},
                {"name": "mistral:latest"}
            ]
        }
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = Mock()
            
            models = provider.list_models()
            assert len(models) == 3
            assert "phi3:mini" in models
            assert "llama2:7b" in models
            assert "mistral:latest" in models

    def test_ollama_list_models_failure(self):
        """Test list_models when service is down."""
        provider = OllamaLLM()
        
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()
            
            models = provider.list_models()
            assert models == []


class TestOllamaIntegration:
    """Integration tests for Ollama through LLMProvider."""

    def test_llm_provider_ollama_initialization(self):
        """Test LLMProvider creates OllamaLLM correctly."""
        llm = LLMProvider(provider="ollama", model="phi3:mini")
        assert llm.provider == "ollama"
        assert llm.model == "phi3:mini"
        
        client = llm._get_client()
        assert isinstance(client, OllamaLLM)
        assert client.model == "phi3:mini"

    def test_llm_provider_ollama_custom_config(self):
        """Test LLMProvider with custom Ollama config."""
        llm = LLMProvider(
            provider="ollama",
            model="llama2",
            base_url="http://custom:8080",
            timeout=120,
            num_ctx=4096
        )
        
        client = llm._get_client()
        assert isinstance(client, OllamaLLM)
        assert client.model == "llama2"
        assert client.base_url == "http://custom:8080"
        assert client.timeout == 120
        assert client.num_ctx == 4096

    @pytest.mark.asyncio
    async def test_llm_provider_ollama_chat(self):
        """Test chat through LLMProvider with Ollama."""
        llm = LLMProvider(provider="ollama", model="phi3:mini")
        
        mock_response = {
            "model": "phi3:mini",
            "message": {"role": "assistant", "content": "Test response"},
            "done": True
        }
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = Mock()
            
            messages = [{"role": "user", "content": "Hello"}]
            result = await llm.chat(messages)
            
            assert result["content"] == "Test response"
            assert result["provider"] == "ollama"
            assert result["usage"]["cost"] == 0.0

    def test_get_llm_ollama(self):
        """Test factory function with Ollama provider."""
        llm = get_llm(provider="ollama", model="phi3:mini")
        assert isinstance(llm, LLMProvider)
        assert llm.provider == "ollama"
        assert llm.model == "phi3:mini"


class TestOllamaE2E:
    """End-to-end tests with real Ollama instance (skippable)."""

    @staticmethod
    def is_ollama_running():
        """Check if Ollama is running locally."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def has_phi3_model():
        """Check if phi3:mini model is available."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return any("phi3" in name for name in model_names)
        except Exception:
            return False

    @pytest.mark.skipif(not is_ollama_running.__func__(), reason="Ollama not running")
    @pytest.mark.asyncio
    async def test_real_ollama_health_check(self):
        """Test health check with real Ollama instance."""
        provider = OllamaLLM(model="phi3:mini")
        result = provider.health_check()
        assert isinstance(result, bool)

    @pytest.mark.skipif(not is_ollama_running.__func__() or not has_phi3_model.__func__(), 
                        reason="Ollama not running or phi3:mini not available")
    @pytest.mark.asyncio
    async def test_real_ollama_chat(self):
        """Test chat with real Ollama instance."""
        provider = OllamaLLM(model="phi3:mini")
        
        messages = [{"role": "user", "content": "Say hello in exactly one word"}]
        result = await provider.chat(messages)
        
        assert result["content"]
        assert len(result["content"]) > 0
        assert result["provider"] == "ollama"
        assert result["model"] == "phi3:mini"
        assert result["usage"]["total_tokens"] > 0
        assert result["usage"]["cost"] == 0.0

    @pytest.mark.skipif(not is_ollama_running.__func__() or not has_phi3_model.__func__(), 
                        reason="Ollama not running or phi3:mini not available")
    @pytest.mark.asyncio
    async def test_real_ollama_streaming(self):
        """Test streaming with real Ollama instance."""
        provider = OllamaLLM(model="phi3:mini")
        
        messages = [{"role": "user", "content": "Count from 1 to 3"}]
        chunks = []
        
        async for chunk in provider.chat_stream(messages):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        full_response = "".join(c["content"] for c in chunks)
        assert len(full_response) > 0
        assert chunks[-1]["done"] is True

    @pytest.mark.skipif(not is_ollama_running.__func__(), reason="Ollama not running")
    def test_real_ollama_list_models(self):
        """Test listing models with real Ollama instance."""
        provider = OllamaLLM()
        models = provider.list_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        # Should have at least one model if Ollama is running

