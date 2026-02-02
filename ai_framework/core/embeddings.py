"""
Embedding Provider Abstraction for RAG.

This module provides a unified interface for generating embeddings
across multiple providers (OpenAI, Gemini, Ollama) using LangChain.

Story 7.2: Embedding Provider Abstraction (LangChain)
"""

import os
import logging
from typing import Optional
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


# Global singleton instance
_embeddings_instance: Optional[Embeddings] = None
_provider_name: Optional[str] = None


def get_embeddings() -> Embeddings:
    """
    Get or create the embeddings instance (singleton).
    
    Automatically selects embedding provider based on AI_SDK_LLM_PROVIDER
    environment variable.
    
    Returns:
        Embeddings: LangChain embeddings instance
    """
    global _embeddings_instance, _provider_name
    
    if _embeddings_instance is None:
        provider = os.getenv("AI_SDK_LLM_PROVIDER", "openai").lower()
        _provider_name = provider
        
        try:
            if provider == "openai":
                _embeddings_instance = _create_openai_embeddings()
            elif provider == "gemini":
                _embeddings_instance = _create_gemini_embeddings()
            elif provider == "ollama":
                _embeddings_instance = _create_ollama_embeddings()
            else:
                logger.warning(f"Unknown provider '{provider}', falling back to HuggingFace")
                _embeddings_instance = _create_huggingface_embeddings()
                _provider_name = "huggingface"
        except Exception as e:
            logger.error(f"Failed to initialize {provider} embeddings: {e}")
            logger.info("Falling back to HuggingFace local embeddings")
            _embeddings_instance = _create_huggingface_embeddings()
            _provider_name = "huggingface"
    
    return _embeddings_instance


def reset_embeddings():
    """Reset the singleton instance (for testing)."""
    global _embeddings_instance, _provider_name
    _embeddings_instance = None
    _provider_name = None


def get_provider_name() -> str:
    """Get the name of the current provider."""
    global _provider_name
    if _embeddings_instance is None:
        get_embeddings()  # Initialize if not already done
    return _provider_name or "unknown"


def get_embedding_dimensions() -> int:
    """
    Get the dimensionality of embeddings for the current provider.
    
    Returns:
        int: Number of dimensions in each embedding vector
    """
    global _provider_name
    
    if _provider_name is None:
        get_embeddings()  # Initialize
    
    provider_dims = {
        "openai": 1536,
        "gemini": 768,
        "ollama": 768,
        "huggingface": 384
    }
    
    return provider_dims.get(_provider_name or "huggingface", 384)


def _create_openai_embeddings() -> OpenAIEmbeddings:
    """Create OpenAI embeddings."""
    model = os.getenv("AI_SDK_EMBEDDING_MODEL", "text-embedding-3-small")
    api_key = os.getenv("AI_SDK_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError(
            "OpenAI API key not found. Set AI_SDK_OPENAI_API_KEY or OPENAI_API_KEY"
        )
    
    logger.info(f"Using OpenAI embeddings: {model} (1536 dims)")
    return OpenAIEmbeddings(model=model)


def _create_gemini_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Create Google Gemini embeddings."""
    model = os.getenv("AI_SDK_EMBEDDING_MODEL", "models/embedding-001")
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError("Google API key not found. Set GOOGLE_API_KEY")
    
    logger.info(f"Using Gemini embeddings: {model} (768 dims)")
    return GoogleGenerativeAIEmbeddings(model=model)


def _create_ollama_embeddings() -> Embeddings:
    """Create Ollama embeddings (local)."""
    try:
        from langchain_community.embeddings import OllamaEmbeddings
    except ImportError:
        logger.warning("OllamaEmbeddings not available, using HuggingFace")
        return _create_huggingface_embeddings()
    
    model = os.getenv("AI_SDK_EMBEDDING_MODEL", "nomic-embed-text")
    base_url = os.getenv("AI_SDK_OLLAMA_BASE_URL", "http://localhost:11434")
    
    logger.info(f"Using Ollama embeddings: {model} at {base_url} (768 dims)")
    return OllamaEmbeddings(model=model, base_url=base_url)


def _create_huggingface_embeddings() -> HuggingFaceEmbeddings:
    """Create HuggingFace embeddings (local fallback)."""
    model = os.getenv("AI_SDK_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    logger.info(f"Using HuggingFace embeddings: {model} (384 dims, local)")
    return HuggingFaceEmbeddings(
        model_name=model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
