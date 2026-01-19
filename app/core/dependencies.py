"""Dependency injection utilities for FastAPI.

Database session and other dependencies used across API endpoints.
"""
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.security import verify_api_key_in_db
from ai_framework.llm import get_llm, BaseLLM
from ai_framework.core.executor import AgentExecutor

# Database session factory - set by main.py
SessionLocal = None

# Test API key (used for testing, not in production)
TEST_API_KEY = "test-key-e2e5c8a9d7b2f4e1c3a6d9b2e5f8c1a4"
TEST_API_KEY_HASH = "a" * 64  # SHA-256 hash (placeholder)


def get_db() -> Session:
    """Get database session for dependency injection.
    
    Yields:
        SQLAlchemy session for database operations
    """
    global SessionLocal
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(session_factory) -> None:
    """Initialize database session factory.
    
    Args:
        session_factory: SQLAlchemy sessionmaker instance
    """
    global SessionLocal
    SessionLocal = session_factory


def get_llm_service() -> BaseLLM:
    """Get LLM service for implementation.
    
    Uses settings to determine provider and model.
    """
    from ai_framework.core.config import settings
    return get_llm(
        provider=settings.llm_provider,
        model=settings.llm_model,
        temperature=0.7
    )


def get_executor(llm: BaseLLM = Depends(get_llm_service)) -> AgentExecutor:
    """Get AgentExecutor for processing messages."""
    return AgentExecutor(llm=llm)
