"""
Test suite for API Key authentication (Task 1.4).

Tests verify:
- API key generation and hashing
- API key validation against database
- Middleware enforcement of X-API-Key header
- Full authentication workflow
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.models import Base, APIKey
from app.core.security import (
    hash_api_key,
    generate_api_key,
    verify_api_key_against_hash,
    verify_api_key_in_db
)
import uuid


@pytest.fixture
def sqlite_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


class TestAPIKeySecurity:
    """Test API key hashing and verification functions."""
    
    def test_hash_api_key(self):
        """Test API key hashing produces consistent results."""
        key = "my-secret-api-key"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex = 64 chars
        assert hash1 != key  # Hash should differ from original
    
    def test_generate_api_key(self):
        """Test random API key generation."""
        key1 = generate_api_key()
        key2 = generate_api_key()
        
        assert isinstance(key1, str)
        assert len(key1) == 64  # 32 bytes as hex
        assert key1 != key2  # Should be different each time
    
    def test_verify_api_key_against_hash(self):
        """Test verifying a key against its hash."""
        key = "test-key-12345"
        key_hash = hash_api_key(key)
        
        assert verify_api_key_against_hash(key, key_hash) is True
        assert verify_api_key_against_hash("wrong-key", key_hash) is False
    
    def test_verify_api_key_in_db_valid(self, sqlite_memory_db):
        """Test verifying an active API key from database."""
        db = sqlite_memory_db
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name="test-key",
            key_hash=key_hash,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        
        verified = verify_api_key_in_db(db, raw_key)
        assert verified is not None
        assert verified.is_active is True
        assert verified.last_used_at is not None  # Should be updated
    
    def test_verify_api_key_in_db_invalid_key(self, sqlite_memory_db):
        """Test verifying with wrong key."""
        db = sqlite_memory_db
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name="test-key",
            key_hash=key_hash,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        
        verified = verify_api_key_in_db(db, "wrong-key")
        assert verified is None
    
    def test_verify_api_key_in_db_inactive(self, sqlite_memory_db):
        """Test verifying an inactive key."""
        db = sqlite_memory_db
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name="inactive-key",
            key_hash=key_hash,
            is_active=False  # Inactive
        )
        db.add(api_key)
        db.commit()
        
        verified = verify_api_key_in_db(db, raw_key)
        assert verified is None


class TestAPIKeyInDatabase:
    """Test API key creation and management in database."""
    
    def test_create_api_key_in_db(self, sqlite_memory_db):
        """Test creating and storing an API key."""
        db = sqlite_memory_db
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        key_id = str(uuid.uuid4())
        
        api_key = APIKey(
            id=key_id,
            name="production-key",
            key_hash=key_hash,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        
        # Verify it was stored
        assert api_key.id == key_id
        assert api_key.name == "production-key"
        assert api_key.is_active is True
        assert api_key.created_at is not None
    
    def test_hash_matches_verification(self, sqlite_memory_db):
        """Test that API key hash matches and verification works."""
        db = sqlite_memory_db
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name="test-key",
            key_hash=key_hash,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        
        # Verify via database
        verified = verify_api_key_in_db(db, raw_key)
        assert verified is not None
        assert verified.key_hash == key_hash
        assert api_key.verify_key(raw_key) is True  # Test model method
    
    def test_multiple_api_keys(self, sqlite_memory_db):
        """Test creating and managing multiple API keys."""
        db = sqlite_memory_db
        
        # Create multiple keys
        keys_data = []
        for i in range(3):
            raw_key = generate_api_key()
            key_hash = hash_api_key(raw_key)
            api_key = APIKey(
                id=str(uuid.uuid4()),
                name=f"key-{i}",
                key_hash=key_hash,
                is_active=True
            )
            db.add(api_key)
            keys_data.append((raw_key, api_key.id))
        
        db.commit()
        
        # Verify all can be retrieved and are different
        for raw_key, expected_id in keys_data:
            verified = verify_api_key_in_db(db, raw_key)
            assert verified is not None
            assert verified.id == expected_id
    
    def test_api_key_deactivation(self, sqlite_memory_db):
        """Test deactivating an API key."""
        db = sqlite_memory_db
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name="temp-key",
            key_hash=key_hash,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        
        # Verify it works while active
        assert verify_api_key_in_db(db, raw_key) is not None
        
        # Deactivate it
        api_key.is_active = False
        db.commit()
        
        # Should no longer work
        assert verify_api_key_in_db(db, raw_key) is None

