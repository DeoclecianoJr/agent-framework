"""
Embedding providers for semantic search.

Story 7.7: Semantic Search API
"""

from .base import EmbeddingProvider, EmbeddingResult
from .factory import EmbeddingProviderFactory

__all__ = [
    'EmbeddingProvider',
    'EmbeddingResult',
    'EmbeddingProviderFactory',
]
