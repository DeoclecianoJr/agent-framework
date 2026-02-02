"""
Base embedding provider interface.

Story 7.7: Semantic Search API
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """
    Result of an embedding operation.
    
    Attributes:
        embedding: Vector representation of text
        model: Model name used for embedding
        tokens: Number of tokens processed (if available)
        metadata: Additional provider-specific metadata
    """
    embedding: List[float]
    model: str
    tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    
    All embedding providers (OpenAI, Gemini, local models) must implement
    this interface to ensure consistent behavior across the application.
    
    Usage:
        provider = OpenAIEmbeddingProvider(api_key="sk-...")
        result = provider.embed_text("Hello world")
        print(f"Vector dimension: {len(result.embedding)}")
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize embedding provider.
        
        Args:
            api_key: API key for authentication (provider-specific)
            model: Model name to use (provider-specific)
        """
        self.api_key = api_key
        self.model = model or self.get_default_model()
    
    @abstractmethod
    def embed_text(self, text: str, **kwargs) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            **kwargs: Provider-specific parameters
            
        Returns:
            EmbeddingResult: Embedding result with vector and metadata
            
        Raises:
            ValueError: If text is empty or invalid
            RuntimeError: If API call fails
        """
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str], **kwargs) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to embed
            **kwargs: Provider-specific parameters
            
        Returns:
            List[EmbeddingResult]: List of embedding results
            
        Raises:
            ValueError: If texts is empty or contains invalid entries
            RuntimeError: If API call fails
        """
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get embedding vector dimension for current model.
        
        Returns:
            int: Vector dimension (e.g., 1536 for text-embedding-3-small)
        """
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """
        Get default model name for this provider.
        
        Returns:
            str: Default model name
        """
        pass
    
    def validate_text(self, text: str) -> None:
        """
        Validate input text before embedding.
        
        Args:
            text: Text to validate
            
        Raises:
            ValueError: If text is invalid
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
    
    def validate_batch(self, texts: List[str]) -> None:
        """
        Validate batch input before embedding.
        
        Args:
            texts: List of texts to validate
            
        Raises:
            ValueError: If batch is invalid
        """
        if not texts:
            raise ValueError("Batch cannot be empty")
        
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} is empty")


class EmbeddingError(Exception):
    """Base exception for embedding operations."""
    pass


class EmbeddingAPIError(EmbeddingError):
    """Exception raised when API call fails."""
    pass


class EmbeddingValidationError(EmbeddingError):
    """Exception raised when input validation fails."""
    pass
