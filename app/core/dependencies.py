"""Dependency injection utilities for FastAPI.
Production-ready database and service dependencies.
"""
import os
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.security import verify_api_key_in_db
from ai_framework.llm import get_llm, BaseLLM
from ai_framework.core.executor import AgentExecutor

# Global database components
_engine = None
_SessionLocal = None

# Export SessionLocal for RAG integration in executor
SessionLocal = None

# Test API key (used for testing, not in production)
TEST_API_KEY = "test-key-e2e5c8a9d7b2f4e1c3a6d9b2e5f8c1a4"
TEST_API_KEY_HASH = "a" * 64  # SHA-256 hash (placeholder)


def _ensure_db_initialized():
    """Ensure database connection is initialized."""
    global _engine, _SessionLocal, SessionLocal
    if _engine is None:
        database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres123@postgres:5432/ai_framework")
        _engine = create_engine(database_url)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        SessionLocal = _SessionLocal  # Export for use in executor


def get_db():
    """Get database session for dependency injection.
    
    Yields:
        SQLAlchemy session for database operations
    """
    _ensure_db_initialized()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
