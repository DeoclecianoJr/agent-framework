"""
Simple embedding tests that don't load heavy models.

Story 7.7: Semantic Search API
"""

import pytest
from ai_framework.core.embeddings import EmbeddingProviderFactory
from ai_framework.core.embeddings.base import EmbeddingProvider, EmbeddingResult


class TestEmbeddingFactory:
    """Test embedding factory without loading models."""
    
    def test_list_providers(self):
        """Factory lists available providers."""
        providers = EmbeddingProviderFactory.list_providers()
        assert 'openai' in providers
        assert 'gemini' in providers
        assert 'local' in providers
    
    def test_unknown_provider_raises_error(self):
        """Unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            EmbeddingProviderFactory.create_provider('unknown')
    
    def test_openai_requires_api_key(self):
        """OpenAI provider requires API key."""
        with pytest.raises(ValueError, match="API key not provided"):
            EmbeddingProviderFactory.create_provider('openai')
    
    def test_gemini_requires_api_key(self):
        """Gemini provider requires API key."""
        with pytest.raises(ValueError, match="API key not provided"):
            EmbeddingProviderFactory.create_provider('gemini')
    
    def test_openai_with_fake_key_creates_provider(self):
        """OpenAI provider can be created with API key."""
        provider = EmbeddingProviderFactory.create_provider('openai', api_key='fake-key')
        assert provider is not None
        assert provider.model == 'text-embedding-3-small'
        assert provider.get_dimension() == 1536
    
    def test_gemini_with_fake_key_creates_provider(self):
        """Gemini provider can be created with API key."""
        provider = EmbeddingProviderFactory.create_provider('gemini', api_key='fake-key')
        assert provider is not None
        assert provider.model == 'models/text-embedding-004'
        assert provider.get_dimension() == 768


class TestEmbeddingBase:
    """Test base embedding classes."""
    
    def test_embedding_result_structure(self):
        """EmbeddingResult has expected fields."""
        result = EmbeddingResult(
            embedding=[0.1, 0.2, 0.3],
            model='test-model',
            tokens=10,
            metadata={'key': 'value'}
        )
        assert len(result.embedding) == 3
        assert result.model == 'test-model'
        assert result.tokens == 10
        assert result.metadata['key'] == 'value'
    
    def test_embedding_result_optional_fields(self):
        """EmbeddingResult works with minimal fields."""
        result = EmbeddingResult(
            embedding=[0.1],
            model='test'
        )
        assert result.tokens is None
        assert result.metadata is None


class TestProviderDimensions:
    """Test provider dimension configurations."""
    
    def test_openai_small_dimension(self):
        """OpenAI text-embedding-3-small has 1536 dimensions."""
        provider = EmbeddingProviderFactory.create_provider(
            'openai',
            api_key='fake',
            model='text-embedding-3-small'
        )
        assert provider.get_dimension() == 1536
    
    def test_openai_large_dimension(self):
        """OpenAI text-embedding-3-large has 3072 dimensions."""
        provider = EmbeddingProviderFactory.create_provider(
            'openai',
            api_key='fake',
            model='text-embedding-3-large'
        )
        assert provider.get_dimension() == 3072
    
    def test_gemini_dimension(self):
        """Gemini text-embedding-004 has 768 dimensions."""
        provider = EmbeddingProviderFactory.create_provider(
            'gemini',
            api_key='fake'
        )
        assert provider.get_dimension() == 768


class TestProviderValidation:
    """Test input validation."""
    
    def test_empty_text_raises_error(self):
        """Empty text raises ValueError."""
        provider = EmbeddingProviderFactory.create_provider('openai', api_key='fake')
        
        with pytest.raises(ValueError, match="cannot be empty"):
            provider.validate_text("")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            provider.validate_text("   ")
    
    def test_empty_batch_raises_error(self):
        """Empty batch raises ValueError."""
        provider = EmbeddingProviderFactory.create_provider('openai', api_key='fake')
        
        with pytest.raises(ValueError, match="cannot be empty"):
            provider.validate_batch([])
    
    def test_batch_with_empty_text_raises_error(self):
        """Batch with empty string raises ValueError."""
        provider = EmbeddingProviderFactory.create_provider('openai', api_key='fake')
        
        with pytest.raises(ValueError, match="is empty"):
            provider.validate_batch(["valid", "", "also valid"])


@pytest.mark.skipif(
    True,  # Skip by default - requires model download
    reason="Skipping local provider test to avoid loading heavy models"
)
class TestLocalProvider:
    """Test local provider (SKIPPED to avoid hanging)."""
    
    def test_local_provider_loads(self):
        """Local provider loads without API key."""
        provider = EmbeddingProviderFactory.create_provider('local')
        assert provider is not None
        assert provider.get_dimension() == 384
