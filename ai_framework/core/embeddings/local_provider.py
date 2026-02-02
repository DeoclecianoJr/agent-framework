"""
Local embedding provider using sentence-transformers.

Story 7.7: Semantic Search API
"""

from typing import List, Optional
import logging
from sentence_transformers import SentenceTransformer

from .base import EmbeddingProvider, EmbeddingResult, EmbeddingAPIError

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.
    
    No API key required - runs locally on CPU/GPU.
    
    Supported models:
    - all-MiniLM-L6-v2: 384 dimensions, fast, good quality
    - paraphrase-multilingual-MiniLM-L12-v2: 384 dimensions, multilingual
    - all-mpnet-base-v2: 768 dimensions, best quality
    
    Usage:
        provider = LocalEmbeddingProvider(model='all-MiniLM-L6-v2')
        result = provider.embed_text("Hello world")
        print(f"Dimensions: {len(result.embedding)}")
    """
    
    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        'all-MiniLM-L6-v2': 384,
        'paraphrase-multilingual-MiniLM-L12-v2': 384,
        'all-mpnet-base-v2': 768,
        'multi-qa-mpnet-base-dot-v1': 768,
    }
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize local embedding provider.
        
        Args:
            api_key: Not used (for interface compatibility)
            model: Model name (default: all-MiniLM-L6-v2)
        """
        super().__init__(api_key, model)
        
        # Load sentence transformer model
        try:
            logger.info(f"Loading local model: {self.model}")
            self.model_instance = SentenceTransformer(self.model)
            logger.info(f"Local embedding provider initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model}: {e}")
            raise EmbeddingAPIError(f"Failed to load local model: {e}")
    
    def get_default_model(self) -> str:
        """Get default local embedding model."""
        return 'all-MiniLM-L6-v2'
    
    def get_dimension(self) -> int:
        """Get embedding dimension for current model."""
        return self.MODEL_DIMENSIONS.get(self.model, 384)
    
    def embed_text(self, text: str, **kwargs) -> EmbeddingResult:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            **kwargs: Additional parameters (normalize_embeddings, etc.)
            
        Returns:
            EmbeddingResult: Embedding result
            
        Raises:
            EmbeddingAPIError: If embedding generation fails
        """
        self.validate_text(text)
        
        try:
            # Generate embedding
            embedding = self.model_instance.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=kwargs.get('normalize_embeddings', True)
            )
            
            return EmbeddingResult(
                embedding=embedding.tolist(),
                model=self.model,
                tokens=None,  # Local models don't track tokens
                metadata={
                    'provider': 'local',
                    'dimension': len(embedding),
                }
            )
            
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise EmbeddingAPIError(f"Failed to generate embedding: {e}")
    
    def embed_batch(self, texts: List[str], **kwargs) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.
        
        Batch processing is much faster for local models.
        
        Args:
            texts: List of texts to embed
            **kwargs: Additional parameters
            
        Returns:
            List[EmbeddingResult]: List of embedding results
            
        Raises:
            EmbeddingAPIError: If embedding generation fails
        """
        self.validate_batch(texts)
        
        try:
            # Generate embeddings in batch (faster)
            embeddings = self.model_instance.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=kwargs.get('normalize_embeddings', True),
                batch_size=kwargs.get('batch_size', 32),
                show_progress_bar=kwargs.get('show_progress_bar', False)
            )
            
            # Convert to EmbeddingResult objects
            results = []
            for i, embedding in enumerate(embeddings):
                results.append(EmbeddingResult(
                    embedding=embedding.tolist(),
                    model=self.model,
                    tokens=None,
                    metadata={
                        'provider': 'local',
                        'index': i,
                        'batch_size': len(texts),
                        'dimension': len(embedding),
                    }
                ))
            
            logger.info(f"Generated {len(results)} embeddings using local model {self.model}")
            return results
            
        except Exception as e:
            logger.error(f"Local batch embedding failed: {e}")
            raise EmbeddingAPIError(f"Failed to generate batch embeddings: {e}")
