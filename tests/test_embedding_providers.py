"""
Tests for Story 7.7: Semantic Search API - Embedding Providers

Tests for custom embedding providers (OpenAI, Gemini, Local)
and EmbeddingProviderFactory.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from ai_framework.core.embeddings.base import EmbeddingProvider, EmbeddingResult, EmbeddingAPIError
from ai_framework.core.embeddings.openai_provider import OpenAIEmbeddingProvider
from ai_framework.core.embeddings.gemini_provider import GeminiEmbeddingProvider
from ai_framework.core.embeddings.local_provider import LocalEmbeddingProvider
from ai_framework.core.embeddings.factory import EmbeddingProviderFactory


# ============================================================================
# Provider Factory Tests
# ============================================================================

class TestEmbeddingProviderFactory:
    """Test embedding provider factory."""
    
    def test_list_providers(self):
        """Test listing available providers."""
        providers = EmbeddingProviderFactory.list_providers()
        assert 'openai' in providers
        assert 'gemini' in providers
        assert 'local' in providers
        assert len(providers) >= 3
    
    def test_create_local_provider(self):
        """Test creating local provider (no API key needed)."""
        provider = EmbeddingProviderFactory.create_provider('local')
        assert isinstance(provider, LocalEmbeddingProvider)
        assert provider.model == 'all-MiniLM-L6-v2'
        assert provider.get_dimension() == 384
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'fake-key'})
    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = EmbeddingProviderFactory.create_provider('openai')
        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert provider.model == 'text-embedding-3-small'
        assert provider.get_dimension() == 1536
    
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'fake-key'})
    def test_create_gemini_provider(self):
        """Test creating Gemini provider."""
        provider = EmbeddingProviderFactory.create_provider('gemini')
        assert isinstance(provider, GeminiEmbeddingProvider)
        assert provider.model == 'models/text-embedding-004'
        assert provider.get_dimension() == 768
    
    def test_create_provider_with_custom_model(self):
        """Test creating provider with custom model."""
        provider = EmbeddingProviderFactory.create_provider(
            'local',
            model='all-mpnet-base-v2'
        )
        assert provider.model == 'all-mpnet-base-v2'
        assert provider.get_dimension() == 768
    
    def test_create_unknown_provider_fails(self):
        """Test that unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            EmbeddingProviderFactory.create_provider('unknown-provider')
    
    def test_register_custom_provider(self):
        """Test registering custom provider."""
        class CustomProvider(EmbeddingProvider):
            def get_default_model(self):
                return 'custom-model'
            def get_dimension(self):
                return 512
            def embed_text(self, text, **kwargs):
                return EmbeddingResult([0.1] * 512, 'custom-model')
            def embed_batch(self, texts, **kwargs):
                return [self.embed_text(t) for t in texts]
        
        EmbeddingProviderFactory.register_provider('custom', CustomProvider)
        assert 'custom' in EmbeddingProviderFactory.list_providers()
        
        provider = EmbeddingProviderFactory.create_provider('custom')
        assert isinstance(provider, CustomProvider)


# ============================================================================
# Local Provider Tests
# ============================================================================

class TestLocalEmbeddingProvider:
    """Test local embedding provider."""
    
    def test_provider_initialization(self):
        """Test provider initializes correctly."""
        provider = LocalEmbeddingProvider()
        assert provider.model == 'all-MiniLM-L6-v2'
        assert provider.get_dimension() == 384
        assert provider.model_instance is not None
    
    def test_embed_single_text(self):
        """Test embedding single text."""
        provider = LocalEmbeddingProvider()
        result = provider.embed_text("Hello world")
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 384
        assert result.model == 'all-MiniLM-L6-v2'
        assert all(isinstance(x, float) for x in result.embedding)
    
    def test_embed_batch(self):
        """Test batch embedding."""
        provider = LocalEmbeddingProvider()
        texts = ["First text", "Second text", "Third text"]
        results = provider.embed_batch(texts)
        
        assert len(results) == 3
        assert all(isinstance(r, EmbeddingResult) for r in results)
        assert all(len(r.embedding) == 384 for r in results)
    
    def test_embed_empty_text_fails(self):
        """Test that empty text raises error."""
        provider = LocalEmbeddingProvider()
        with pytest.raises(ValueError, match="Text cannot be empty"):
            provider.embed_text("")
    
    def test_embed_empty_batch_fails(self):
        """Test that empty batch raises error."""
        provider = LocalEmbeddingProvider()
        with pytest.raises(ValueError, match="Batch cannot be empty"):
            provider.embed_batch([])
    
    def test_different_models(self):
        """Test different local models."""
        models_dims = {
            'all-MiniLM-L6-v2': 384,
            'all-mpnet-base-v2': 768,
        }
        
        for model, expected_dim in models_dims.items():
            provider = LocalEmbeddingProvider(model=model)
            assert provider.get_dimension() == expected_dim
            
            result = provider.embed_text("Test text")
            assert len(result.embedding) == expected_dim
    
    def test_embedding_consistency(self):
        """Test that same text produces same embedding."""
        provider = LocalEmbeddingProvider()
        text = "Consistent text for testing"
        
        result1 = provider.embed_text(text)
        result2 = provider.embed_text(text)
        
        # Embeddings should be identical for same text
        assert result1.embedding == result2.embedding
    
    def test_different_texts_produce_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        provider = LocalEmbeddingProvider()
        
        result1 = provider.embed_text("Hello world")
        result2 = provider.embed_text("Goodbye world")
        
        # Embeddings should be different
        assert result1.embedding != result2.embedding


# ============================================================================
# OpenAI Provider Tests (Mocked)
# ============================================================================

class TestOpenAIEmbeddingProvider:
    """Test OpenAI embedding provider with mocked API."""
    
    @patch('ai_framework.core.embeddings.openai_provider.OpenAI')
    def test_provider_initialization(self, mock_openai):
        """Test provider initializes with API key."""
        provider = OpenAIEmbeddingProvider(api_key='fake-key')
        assert provider.model == 'text-embedding-3-small'
        assert provider.get_dimension() == 1536
        mock_openai.assert_called_once_with(api_key='fake-key')
    
    @patch('ai_framework.core.embeddings.openai_provider.OpenAI')
    def test_embed_single_text(self, mock_openai):
        """Test embedding single text."""
        # Mock OpenAI response
        mock_client = Mock()
        mock_embedding_data = Mock()
        mock_embedding_data.embedding = [0.1] * 1536
        mock_embedding_data.index = 0
        
        mock_response = Mock()
        mock_response.data = [mock_embedding_data]
        mock_response.usage.total_tokens = 10
        
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = OpenAIEmbeddingProvider(api_key='fake-key')
        result = provider.embed_text("Hello world")
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 1536
        assert result.tokens == 10
        assert result.model == 'text-embedding-3-small'
    
    @patch('ai_framework.core.embeddings.openai_provider.OpenAI')
    def test_embed_batch(self, mock_openai):
        """Test batch embedding."""
        # Mock batch response
        mock_client = Mock()
        mock_data = []
        for i in range(3):
            mock_embedding = Mock()
            mock_embedding.embedding = [0.1 * (i + 1)] * 1536
            mock_embedding.index = i
            mock_data.append(mock_embedding)
        
        mock_response = Mock()
        mock_response.data = mock_data
        mock_response.usage.total_tokens = 30
        
        mock_client.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = OpenAIEmbeddingProvider(api_key='fake-key')
        results = provider.embed_batch(["Text 1", "Text 2", "Text 3"])
        
        assert len(results) == 3
        assert all(isinstance(r, EmbeddingResult) for r in results)
        # Note: tokens is total for batch, not per result
        assert any(r.tokens == 30 for r in results) or all(r.tokens is None for r in results)
    
    def test_missing_api_key_fails(self):
        """Test that missing API key raises error."""
        with pytest.raises(ValueError, match="OpenAI API key"):
            OpenAIEmbeddingProvider()
    
    @patch('ai_framework.core.embeddings.openai_provider.OpenAI')
    def test_different_models(self, mock_openai):
        """Test different OpenAI models."""
        models = {
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072,
            'text-embedding-ada-002': 1536,
        }
        
        for model, expected_dim in models.items():
            provider = OpenAIEmbeddingProvider(api_key='fake-key', model=model)
            assert provider.model == model
            assert provider.get_dimension() == expected_dim
    
    @patch('ai_framework.core.embeddings.openai_provider.OpenAI')
    def test_api_error_handling(self, mock_openai):
        """Test API error handling."""
        mock_client = Mock()
        mock_client.embeddings.create.side_effect = Exception("API Error")
        mock_openai.return_value = mock_client
        
        provider = OpenAIEmbeddingProvider(api_key='fake-key')
        with pytest.raises(EmbeddingAPIError, match="Failed to generate embedding"):
            provider.embed_text("Test")


# ============================================================================
# Gemini Provider Tests (Mocked)
# ============================================================================

class TestGeminiEmbeddingProvider:
    """Test Gemini embedding provider with mocked API."""
    
    @patch('ai_framework.core.embeddings.gemini_provider.genai.Client')
    def test_provider_initialization(self, mock_genai):
        """Test provider initializes with API key."""
        provider = GeminiEmbeddingProvider(api_key='fake-key')
        assert provider.model == 'models/text-embedding-004'
        assert provider.get_dimension() == 768
        mock_genai.assert_called_once_with(api_key='fake-key')
    
    @patch('ai_framework.core.embeddings.gemini_provider.genai.Client')
    def test_embed_single_text(self, mock_genai):
        """Test embedding single text."""
        # Mock Gemini response
        mock_client = Mock()
        mock_embedding = Mock()
        mock_embedding.values = [0.1] * 768
        
        mock_response = Mock()
        mock_response.embeddings = [mock_embedding]
        
        mock_client.models.embed_content.return_value = mock_response
        mock_genai.return_value = mock_client
        
        provider = GeminiEmbeddingProvider(api_key='fake-key')
        result = provider.embed_text("Hello world")
        
        assert isinstance(result, EmbeddingResult)
        assert len(result.embedding) == 768
        assert result.model == 'models/text-embedding-004'
    
    @patch('ai_framework.core.embeddings.gemini_provider.genai.Client')
    def test_embed_batch(self, mock_genai):
        """Test batch embedding."""
        mock_client = Mock()
        mock_embeddings = []
        for i in range(3):
            mock_emb = Mock()
            mock_emb.values = [0.1 * (i + 1)] * 768
            mock_embeddings.append(mock_emb)
        
        mock_response = Mock()
        mock_response.embeddings = mock_embeddings
        
        mock_client.models.embed_content.return_value = mock_response
        mock_genai.return_value = mock_client
        
        provider = GeminiEmbeddingProvider(api_key='fake-key')
        results = provider.embed_batch(["Text 1", "Text 2", "Text 3"])
        
        assert len(results) == 3
        assert all(isinstance(r, EmbeddingResult) for r in results)
    
    def test_missing_api_key_fails(self):
        """Test that missing API key raises error."""
        with pytest.raises(ValueError, match="Gemini API key"):
            GeminiEmbeddingProvider()
    
    @patch('ai_framework.core.embeddings.gemini_provider.genai.Client')
    def test_task_type_configuration(self, mock_genai):
        """Test different task types."""
        mock_client = Mock()
        mock_embedding = Mock()
        mock_embedding.values = [0.1] * 768
        mock_response = Mock()
        mock_response.embeddings = [mock_embedding]
        mock_client.models.embed_content.return_value = mock_response
        mock_genai.return_value = mock_client
        
        provider = GeminiEmbeddingProvider(api_key='fake-key')
        
        # Test RETRIEVAL_QUERY
        result = provider.embed_text("Query text", task_type="RETRIEVAL_QUERY")
        assert len(result.embedding) == 768
        
        # Test RETRIEVAL_DOCUMENT
        result = provider.embed_text("Document text", task_type="RETRIEVAL_DOCUMENT")
        assert len(result.embedding) == 768


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
