"""
Security module for API key authentication and validation.

Functions:
- hash_api_key: Hash an API key using SHA-256
- generate_api_key: Generate a random secure API key
- verify_api_key: Check if a provided key matches a stored hash
"""

import hashlib
import secrets
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.models import APIKey


def hash_api_key(key: str) -> str:
    """Hash an API key using SHA-256.
    
    Args:
        key: Plain text API key
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    """Generate a new random API key (32 bytes = 256 bits).
    
    Returns:
        Random 64-character hex string suitable for API authentication
    """
    return secrets.token_hex(32)


def verify_api_key_against_hash(key: str, key_hash: str) -> bool:
    """Verify if a provided key matches a stored hash.
    
    Args:
        key: Plain text API key to verify
        key_hash: Stored SHA-256 hash
        
    Returns:
        True if key matches hash, False otherwise
    """
    return hash_api_key(key) == key_hash


def verify_api_key_in_db(db: Session, key: str) -> APIKey | None:
    """Verify an API key against the database.
    
    Args:
        db: SQLAlchemy database session
        key: Plain text API key provided by client
        
    Returns:
        APIKey object if valid and active, None otherwise
    """
    key_hash = hash_api_key(key)
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if api_key and api_key.expires_at is None:
        # Update last_used_at timestamp
        api_key.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return api_key

    
    return None
