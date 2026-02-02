"""
OpenAI embedding provider.

Story 7.7: Semantic Search API
"""

import os
from typing import List, Optional
import logging
from openai import OpenAI

from .base import EmbeddingProvider, EmbeddingResult, EmbeddingAPIError

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3 models.
    
    Supported models:
    - text-embedding-3-small: 1536 dimensions, fastest
    - text-embedding-3-large: 3072 dimensions, best quality
    - text-embedding-ada-002: 1536 dimensions, legacy
    
    Usage:
        provider = OpenAIEmbeddingProvider(
            api_key=os.getenv('OPENAI_API_KEY'),
            model='text-embedding-3-small'
        )
        result = provider.embed_text("Hello world")
        print(result.embedding[:5])  # First 5 dimensions
    """
    
    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        'text-embedding-3-small': 1536,
        'text-embedding-3-large': 3072,
        'text-embedding-ada-002': 1536,
    }
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key (from env if None)
            model: Model name (default: text-embedding-3-small)
        """
        super().__init__(api_key, model)
        
        # Get API key from environment if not provided
        if not self.api_key:
            self.api_key = os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY env var not set")
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info(f"OpenAI embedding provider initialized with model: {self.model}")
    
    def get_default_model(self) -> str:
        """Get default OpenAI embedding model."""
        return 'text-embedding-3-small'
    
    def get_dimension(self) -> int:
        """Get embedding dimension for current model."""
        return self.MODEL_DIMENSIONS.get(self.model, 1536)
    
    def embed_text(self, text: str, **kwargs) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            **kwargs: Additional parameters (user, encoding_format, etc.)
            
        Returns:
            EmbeddingResult: Embedding result
            
        Raises:
            EmbeddingAPIError: If API call fails
        """
        self.validate_text(text)
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                **kwargs
            )
            
            # Extract embedding from response
            embedding_data = response.data[0]
            
            return EmbeddingResult(
                embedding=embedding_data.embedding,
                model=self.model,
                tokens=response.usage.total_tokens if response.usage else None,
                metadata={
                    'index': embedding_data.index,
                    'object': embedding_data.object,
                }
            )
            
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise EmbeddingAPIError(f"Failed to generate embedding: {e}")
    
    def embed_batch(self, texts: List[str], **kwargs) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.
        
        OpenAI supports batching up to 2048 texts per request.
        
        Args:
            texts: List of texts to embed
            **kwargs: Additional parameters
            
        Returns:
            List[EmbeddingResult]: List of embedding results
            
        Raises:
            EmbeddingAPIError: If API call fails
        """
        self.validate_batch(texts)
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                **kwargs
            )
            
            # Convert to EmbeddingResult objects
            results = []
            for embedding_data in response.data:
                results.append(EmbeddingResult(
                    embedding=embedding_data.embedding,
                    model=self.model,
                    tokens=None,  # Total tokens shared across batch
                    metadata={
                        'index': embedding_data.index,
                        'object': embedding_data.object,
                        'batch_size': len(texts),
                        'total_tokens': response.usage.total_tokens if response.usage else None,
                    }
                ))
            
            logger.info(f"Generated {len(results)} embeddings using {self.model}")
            return results
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            raise EmbeddingAPIError(f"Failed to generate batch embeddings: {e}")
