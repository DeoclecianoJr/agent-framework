"""
Embedding provider factory.

Story 7.7: Semantic Search API
"""

import os
from typing import Optional, Dict, Any
import logging

from .base import EmbeddingProvider
from .openai_provider import OpenAIEmbeddingProvider
from .gemini_provider import GeminiEmbeddingProvider
from .local_provider import LocalEmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingProviderFactory:
    """
    Factory for creating embedding providers.
    
    Usage:
        # From environment variables
        provider = EmbeddingProviderFactory.create_provider('openai')
        
        # With explicit config
        provider = EmbeddingProviderFactory.create_provider(
            'gemini',
            api_key='AIza...',
            model='models/text-embedding-004'
        )
        
        # Local (no API key needed)
        provider = EmbeddingProviderFactory.create_provider('local')
    """
    
    # Registry of available providers
    _providers: Dict[str, type] = {
        'openai': OpenAIEmbeddingProvider,
        'gemini': GeminiEmbeddingProvider,
        'local': LocalEmbeddingProvider,
    }
    
    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingProvider:
        """
        Create embedding provider by type.
        
        Args:
            provider_type: Provider type ('openai', 'gemini')
            api_key: API key (from env if None)
            model: Model name (provider default if None)
            **kwargs: Additional provider-specific parameters
            
        Returns:
            EmbeddingProvider: Initialized provider
            
        Raises:
            ValueError: If provider type not supported
        """
        provider_type = provider_type.lower()
        
        if provider_type not in cls._providers:
            available = ', '.join(cls._providers.keys())
            raise ValueError(
                f"Unknown embedding provider: {provider_type}. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._providers[provider_type]
        
        logger.info(f"Creating embedding provider: {provider_type}")
        return provider_class(api_key=api_key, model=model, **kwargs)
    
    @classmethod
    def create_from_agent(cls, agent) -> EmbeddingProvider:
        """
        Create provider from agent configuration.
        
        Args:
            agent: Agent model with embedding config
            
        Returns:
            EmbeddingProvider: Initialized provider
        """
        config = agent.config.get('embedding_provider', {})
        
        provider_type = config.get('type', os.getenv('DEFAULT_EMBEDDING_PROVIDER', 'openai'))
        api_key = config.get('api_key')
        model = config.get('model')
        
        return cls.create_provider(provider_type, api_key=api_key, model=model)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """
        Register a custom embedding provider.
        
        Args:
            name: Provider name
            provider_class: Provider class (must extend EmbeddingProvider)
        """
        if not issubclass(provider_class, EmbeddingProvider):
            raise ValueError(f"{provider_class} must extend EmbeddingProvider")
        
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered embedding provider: {name}")
    
    @classmethod
    def list_providers(cls) -> list:
        """
        List available provider types.
        
        Returns:
            list: List of provider names
        """
        return list(cls._providers.keys())
