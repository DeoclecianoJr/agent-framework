"""
Google Gemini embedding provider.

Story 7.7: Semantic Search API
"""

import os
from typing import List, Optional
import logging
from google import genai
from google.genai import types

from .base import EmbeddingProvider, EmbeddingResult, EmbeddingAPIError

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Google Gemini embedding provider.
    
    Supported models:
    - models/text-embedding-004: 768 dimensions, latest model
    - models/embedding-001: 768 dimensions, legacy
    
    Task types:
    - RETRIEVAL_QUERY: For search queries
    - RETRIEVAL_DOCUMENT: For documents to be indexed
    - SEMANTIC_SIMILARITY: For semantic similarity tasks
    
    Usage:
        provider = GeminiEmbeddingProvider(
            api_key=os.getenv('GEMINI_API_KEY'),
            model='models/text-embedding-004'
        )
        result = provider.embed_text("Hello world", task_type="RETRIEVAL_DOCUMENT")
    """
    
    # Model dimensions
    MODEL_DIMENSIONS = {
        'models/text-embedding-004': 768,
        'models/embedding-001': 768,
    }
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini embedding provider.
        
        Args:
            api_key: Google API key (from env if None)
            model: Model name (default: models/text-embedding-004)
        """
        super().__init__(api_key, model)
        
        # Get API key from environment if not provided
        if not self.api_key:
            self.api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            raise ValueError("Gemini API key not provided and GEMINI_API_KEY env var not set")
        
        # Configure Gemini client
        self.client = genai.Client(api_key=self.api_key)
        
        logger.info(f"Gemini embedding provider initialized with model: {self.model}")
    
    def get_default_model(self) -> str:
        """Get default Gemini embedding model."""
        return 'models/text-embedding-004'
    
    def get_dimension(self) -> int:
        """Get embedding dimension for current model."""
        return self.MODEL_DIMENSIONS.get(self.model, 768)
    
    def embed_text(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT", **kwargs) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            task_type: Task type (RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT, SEMANTIC_SIMILARITY)
            **kwargs: Additional parameters
            
        Returns:
            EmbeddingResult: Embedding result
            
        Raises:
            EmbeddingAPIError: If API call fails
        """
        self.validate_text(text)
        
        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type
                )
            )
            
            return EmbeddingResult(
                embedding=response.embeddings[0].values,
                model=self.model,
                tokens=None,  # Gemini doesn't return token count
                metadata={
                    'task_type': task_type,
                }
            )
            
        except Exception as e:
            logger.error(f"Gemini embedding failed: {e}")
            raise EmbeddingAPIError(f"Failed to generate embedding: {e}")
    
    def embed_batch(
        self, 
        texts: List[str], 
        task_type: str = "RETRIEVAL_DOCUMENT",
        **kwargs
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            task_type: Task type for all texts
            **kwargs: Additional parameters
            
        Returns:
            List[EmbeddingResult]: List of embedding results
            
        Raises:
            EmbeddingAPIError: If API call fails
        """
        self.validate_batch(texts)
        
        try:
            # Gemini's batch embedding
            response = self.client.models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type
                )
            )
            
            # Convert to EmbeddingResult objects
            results = []
            for i, embedding in enumerate(response.embeddings):
                results.append(EmbeddingResult(
                    embedding=embedding.values,
                    model=self.model,
                    tokens=None,
                    metadata={
                        'task_type': task_type,
                        'index': i,
                        'batch_size': len(texts),
                    }
                ))
            
            logger.info(f"Generated {len(results)} embeddings using {self.model}")
            return results
            
        except Exception as e:
            logger.error(f"Gemini batch embedding failed: {e}")
            raise EmbeddingAPIError(f"Failed to generate batch embeddings: {e}")
