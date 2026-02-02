"""Tests for Google Gemini LLM provider implementation (google.genai)."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from ai_framework.core.llm import GeminiLLM, LLMProvider
from ai_framework.core.config import settings


class TestGeminiInitialization:
    """Test Gemini provider initialization."""

    def test_gemini_initialization_with_api_key(self):
        with patch("ai_framework.core.llm.gemini.genai.Client") as mock_client:
            mock_client.return_value = MagicMock()
            provider = GeminiLLM(api_key="test-key", model="gemini-2.5-flash")
            mock_client.assert_called_once_with(api_key="test-key")
            assert provider.model_name == "gemini-2.5-flash"
            assert provider.temperature == 0.7
            assert provider.max_output_tokens == 2048

    def test_gemini_initialization_missing_api_key(self):
        with patch("ai_framework.core.llm.gemini.genai.Client"):
            with patch.object(settings, "google_api_key", None):
                with pytest.raises(ValueError, match="Google API key not provided"):
                    GeminiLLM()

    def test_gemini_initialization_missing_library(self):
        with patch("ai_framework.core.llm.gemini.GEMINI_AVAILABLE", False):
            with pytest.raises(ImportError, match="google-genai not installed"):
                GeminiLLM(api_key="test-key")


class TestGeminiTokenCounting:
    """Test Gemini token counting functionality."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_count_tokens_success(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=10)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        tokens = provider._count_tokens("Hello, world!")

        assert tokens == 10
        client_instance.models.count_tokens.assert_called_once()

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_count_tokens_empty_text(self, mock_client):
        mock_client.return_value = MagicMock()
        provider = GeminiLLM(api_key="test-key")
        tokens = provider._count_tokens("")
        assert tokens == 0

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_count_tokens_fallback(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.count_tokens.side_effect = Exception("API error")
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        tokens = provider._count_tokens("This is a test message")
        assert tokens > 0


class TestGeminiCostCalculation:
    """Test Gemini cost calculation."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_cost_calculation_gemini_free(self, mock_client):
        mock_client.return_value = MagicMock()
        provider = GeminiLLM(api_key="test-key", model="gemini-2.5-flash")
        cost = provider._calculate_cost(10000, 5000)
        assert cost == 0.0

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_cost_calculation_gemini_premium(self, mock_client):
        mock_client.return_value = MagicMock()
        provider = GeminiLLM(api_key="test-key", model="gemini-1.5-pro")
        cost = provider._calculate_cost(1_000_000, 1_000_000)
        assert cost == 3.75


class TestGeminiMessageMapping:
    """Test Gemini message format conversion."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_map_messages_basic(self, mock_client):
        mock_client.return_value = MagicMock()
        provider = GeminiLLM(api_key="test-key")

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]

        mapped = provider._map_messages(messages)
        assert len(mapped) == 2
        assert mapped[0]["role"] == "user"
        assert mapped[1]["role"] == "model"
        assert mapped[0]["parts"] == ["Hello"]
        assert mapped[1]["parts"] == ["Hi there"]

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_map_messages_system_role(self, mock_client):
        mock_client.return_value = MagicMock()
        provider = GeminiLLM(api_key="test-key")

        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"}
        ]

        mapped = provider._map_messages(messages)
        assert len(mapped) == 2
        assert mapped[0]["role"] == "system"
        assert mapped[1]["role"] == "user"


class TestGeminiHealthCheck:
    """Test Gemini health check functionality."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_health_check_success(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=2)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        assert provider.health_check() is True

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_health_check_failure(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.count_tokens.side_effect = Exception("API error")
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        assert provider.health_check() is False


class TestGeminiChatCompletion:
    """Test Gemini chat completion functionality."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, mock_client):
        client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hello! How can I help you?"
        mock_response.candidates = [MagicMock(finish_reason=MagicMock(name="STOP"))]
        client_instance.models.generate_content.return_value = mock_response
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=10)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key", model="gemini-2.5-flash")
        messages = [{"role": "user", "content": "Hello!"}]
        result = await provider.chat(messages)

        assert result["content"] == "Hello! How can I help you?"
        assert result["provider"] == "gemini"
        assert result["model"] == "gemini-2.5-flash"
        assert result["usage"]["prompt_tokens"] > 0
        assert result["usage"]["completion_tokens"] > 0
        assert result["usage"]["cost"] == 0.0

    @patch("ai_framework.core.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_chat_completion_with_system_message(self, mock_client):
        client_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "I am helpful"
        mock_response.candidates = [MagicMock(finish_reason=MagicMock(name="STOP"))]
        client_instance.models.generate_content.return_value = mock_response
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=10)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "What are you?"}
        ]
        result = await provider.chat(messages)

        assert result["content"] == "I am helpful"
        called_args = client_instance.models.generate_content.call_args[1]
        assert "You are helpful" in called_args["contents"]

    @patch("ai_framework.core.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_chat_completion_with_custom_params(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.generate_content.return_value = MagicMock(
            text="Response",
            candidates=[MagicMock(finish_reason=MagicMock(name="STOP"))]
        )
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=5)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        messages = [{"role": "user", "content": "Test"}]

        result = await provider.chat(
            messages,
            temperature=0.5,
            max_output_tokens=1024,
            top_p=0.8,
            top_k=30
        )

        call_kwargs = client_instance.models.generate_content.call_args[1]
        cfg = call_kwargs["config"]
        assert cfg.temperature == 0.5
        assert cfg.max_output_tokens == 1024
        assert cfg.top_p == 0.8
        assert cfg.top_k == 30
        assert result["content"] == "Response"

    @patch("ai_framework.core.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_chat_completion_error_handling(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.generate_content.side_effect = Exception("API error")
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=5)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception, match="API error"):
            await provider.chat(messages)


class TestGeminiStreaming:
    """Test Gemini streaming functionality."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_chat_stream_success(self, mock_client):
        client_instance = MagicMock()
        stream_chunks = [MagicMock(text="Hello "), MagicMock(text="world"), MagicMock(text="!")]
        client_instance.models.generate_content.return_value = stream_chunks
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=10)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        messages = [{"role": "user", "content": "Say hello"}]

        chunks = []
        async for chunk in provider.chat_stream(messages):
            chunks.append(chunk)

        assert len(chunks) == 4
        assert [c["content"] for c in chunks[:3]] == ["Hello ", "world", "!"]
        assert chunks[3]["done"] is True
        assert all(chunk["provider"] == "gemini" for chunk in chunks)

    @patch("ai_framework.core.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_chat_stream_error_handling(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.generate_content.side_effect = Exception("Stream error")
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=5)
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception, match="Stream error"):
            async for _ in provider.chat_stream(messages):
                pass


class TestGeminiListModels:
    """Test Gemini list models functionality."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_list_models_success(self, mock_client):
        client_instance = MagicMock()
        model_a = MagicMock(name="models/gemini-2.5-flash")
        model_a.name = "models/gemini-2.5-flash"
        model_b = MagicMock(name="models/gemini-1.5-pro")
        model_b.name = "models/gemini-1.5-pro"
        client_instance.models.list.return_value = [model_a, model_b]
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        models = provider.list_models()

        assert "gemini-2.5-flash" in models
        assert "gemini-1.5-pro" in models

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_list_models_error(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.list.side_effect = Exception("API error")
        mock_client.return_value = client_instance

        provider = GeminiLLM(api_key="test-key")
        models = provider.list_models()

        assert models == []


class TestLLMProviderGeminiIntegration:
    """Test LLMProvider integration with Gemini."""

    @patch("ai_framework.core.llm.provider.GeminiLLM")
    def test_get_llm_gemini_provider(self, mock_gemini_llm):
        mock_client = Mock()
        mock_gemini_llm.return_value = mock_client

        provider = LLMProvider(provider="gemini", model="gemini-2.5-flash", api_key="test-key")
        client = provider._get_client()

        assert isinstance(client, Mock)
        mock_gemini_llm.assert_called_once()

    @patch("ai_framework.core.llm.gemini.genai.Client")
    @pytest.mark.asyncio
    async def test_chat_with_gemini_provider(self, mock_client):
        client_instance = MagicMock()
        client_instance.models.generate_content.return_value = MagicMock(
            text="Test response",
            candidates=[MagicMock(finish_reason=MagicMock(name="STOP"))]
        )
        client_instance.models.count_tokens.return_value = MagicMock(total_tokens=5)
        mock_client.return_value = client_instance

        provider = LLMProvider(provider="gemini", model="gemini-2.5-flash", api_key="test-key")
        messages = [{"role": "user", "content": "Hello"}]
        result = await provider.chat(messages)

        assert result["provider"] == "gemini"
        assert result["content"] == "Test response"


class TestGeminiConfigurationFromSettings:
    """Test Gemini configuration from settings."""

    @patch("ai_framework.core.llm.gemini.genai.Client")
    def test_gemini_uses_settings(self, mock_client):
        mock_client.return_value = MagicMock()

        with patch.object(settings, "google_api_key", "settings-key"):
            with patch.object(settings, "gemini_temperature", 0.5):
                provider = LLMProvider(provider="gemini", model="gemini-2.5-flash", temperature=0.5)
                assert provider.temperature == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
