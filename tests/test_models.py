"""
Test suite for database models (Task 1.2).

Tests verify:
- Model fields and attributes exist
- Relationships work correctly
- API key generation and hashing
- SQLite in-memory CRUD operations
"""

import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.models import Base, APIKey, Session as DBSession, Message, ToolCall
import uuid


@pytest.fixture
def sqlite_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


class TestSessionModel:
    """Test Session model fields and behavior."""
    
    def test_session_fields_present(self):
        """Verify Session model has all required fields."""
        session = DBSession(
            id=str(uuid.uuid4()),
            agent_id="test_agent",
            user_id="user123",
            attrs={"source": "web", "locale": "en_US"}
        )
        assert session.id
        assert session.agent_id == "test_agent"
        assert session.user_id == "user123"
        assert session.attrs["source"] == "web"
    
    def test_session_create_and_query_sqlite(self, sqlite_memory_db):
        """Test creating and querying Session from SQLite."""
        db = sqlite_memory_db
        session_id = str(uuid.uuid4())
        session = DBSession(
            id=session_id,
            agent_id="test_agent_2",
            attrs={"test": True}
        )
        db.add(session)
        db.commit()
        
        # Query it back
        queried = db.query(DBSession).filter_by(id=session_id).first()
        assert queried is not None
        assert queried.agent_id == "test_agent_2"
        assert queried.attrs["test"] is True
    
    def test_session_timestamps_auto_set(self, sqlite_memory_db):
        """Test that created_at and updated_at are auto-set."""
        db = sqlite_memory_db
        
        session = DBSession(id=str(uuid.uuid4()), agent_id="test")
        before = datetime.now(timezone.utc)
        db.add(session)
        db.commit()
        after = datetime.now(timezone.utc)

        # Force naive if current value is naive (SQLite behavior sometimes)
        created_at = session.created_at
        if created_at.tzinfo is None:
            before = before.replace(tzinfo=None)
            after = after.replace(tzinfo=None)
        
        assert before <= created_at <= after
        
        updated_at = session.updated_at
        if updated_at.tzinfo is None:
            # Re-ensure before/after are naive if they were made aware by a previous check
            before = before.replace(tzinfo=None)
            after = after.replace(tzinfo=None)
            
        assert before <= updated_at <= after


class TestMessageModel:
    """Test Message model fields and relationships."""
    
    def test_message_fields_present(self):
        """Verify Message model has all required fields."""
        msg = Message(
            id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            role="user",
            content="Hello, agent!",
            tokens_used=5,
            attrs={"source": "api"}
        )
        assert msg.id
        assert msg.session_id
        assert msg.role == "user"
        assert msg.content == "Hello, agent!"
        assert msg.tokens_used == 5
    
    def test_message_with_session_relationship(self, sqlite_memory_db):
        """Test Message → Session relationship."""
        db = sqlite_memory_db
        session_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())
        
        # Create session
        session = DBSession(id=session_id, agent_id="test_agent")
        db.add(session)
        db.commit()
        
        # Create message
        msg = Message(id=msg_id, session_id=session_id, role="user", content="Hi")
        db.add(msg)
        db.commit()
        
        queried_msg = db.query(Message).filter_by(id=msg_id).first()
        assert queried_msg.session.id == session_id
        assert queried_msg.session.agent_id == "test_agent"


class TestAPIKeyModel:
    """Test APIKey model fields and methods."""
    
    def test_api_key_fields_present(self):
        """Verify APIKey model has all required fields."""
        key_hash = APIKey.hash_key("test-key")
        key = APIKey(
            id=str(uuid.uuid4()),
            agent_id=str(uuid.uuid4()),
            name="Production Key",
            key_hash=key_hash,
            is_active=True
        )
        assert key.id
        assert key.agent_id
        assert key.name == "Production Key"
        assert key.is_active is True
    
    def test_api_key_generate_key(self):
        """Test random API key generation."""
        key1 = APIKey.generate_key()
        key2 = APIKey.generate_key()
        
        assert isinstance(key1, str)
        assert len(key1) == 64  # 32 bytes as hex
        assert key1 != key2
    
    def test_api_key_hash_key(self):
        """Test API key hashing."""
        key = "my-secret-key"
        hash1 = APIKey.hash_key(key)
        hash2 = APIKey.hash_key(key)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex chars
        assert hash1 != key
    
    def test_api_key_verify(self):
        """Test API key verification."""
        key = "test-api-key-12345"
        key_hash = APIKey.hash_key(key)
        api_key = APIKey(
            id=str(uuid.uuid4()),
            name="Test",
            key_hash=key_hash
        )
        
        assert api_key.verify_key(key) is True
        assert api_key.verify_key("wrong-key") is False
    
    def test_api_key_in_database(self, sqlite_memory_db):
        """Test storing and querying API keys from DB."""
        db = sqlite_memory_db
        key = "secret-key-xyz"
        key_hash = APIKey.hash_key(key)
        key_id = str(uuid.uuid4())
        
        api_key = APIKey(
            id=key_id,
            name="DB Test Key",
            key_hash=key_hash,
            is_active=True
        )
        db.add(api_key)
        db.commit()
        
        queried = db.query(APIKey).filter_by(id=key_id).first()
        assert queried.verify_key(key) is True
        assert queried.is_active is True


class TestToolCallModel:
    """Test ToolCall model fields and relationships."""
    
    def test_tool_call_fields_present(self):
        """Verify ToolCall model has all required fields."""
        call = ToolCall(
            id=str(uuid.uuid4()),
            message_id=str(uuid.uuid4()),
            tool_name="send_email",
            input_args={"to": "user@example.com", "subject": "Hi"},
            output={"status": "sent", "email_id": "123"},
            status="success",
            execution_time_ms=125.5
        )
        assert call.id
        assert call.tool_name == "send_email"
        assert call.input_args["to"] == "user@example.com"
        assert call.status == "success"
        assert call.execution_time_ms == 125.5
    
    def test_tool_call_with_message_relationship(self, sqlite_memory_db):
        """Test ToolCall → Message relationship."""
        db = sqlite_memory_db
        session_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())
        call_id = str(uuid.uuid4())
        
        # Setup: session → message
        session = DBSession(id=session_id, agent_id="test_agent")
        msg = Message(id=msg_id, session_id=session_id, role="assistant", content="I'll call a tool")
        db.add(session)
        db.add(msg)
        db.commit()
        
        # Add tool call
        call = ToolCall(
            id=call_id,
            message_id=msg_id,
            tool_name="get_weather",
            status="success"
        )
        db.add(call)
        db.commit()
        
        queried_call = db.query(ToolCall).filter_by(id=call_id).first()
        assert queried_call.message.role == "assistant"
        assert queried_call.message.session.id == session_id


class TestFullWorkflow:
    """Integration tests for complete CRUD workflows."""
    
    def test_full_session_message_workflow(self, sqlite_memory_db):
        """Test creating a session and messages together."""
        db = sqlite_memory_db
        session_id = str(uuid.uuid4())
        
        # Create session
        session = DBSession(
            id=session_id,
            agent_id="support_agent",
            user_id="customer123"
        )
        db.add(session)
        db.commit()
        
        # Add messages
        user_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content="I need help"
        )
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content="I'm here to help. What's your issue?",
            tokens_used=15
        )
        db.add(user_msg)
        db.add(assistant_msg)
        db.commit()
        
        # Query back and verify relationships
        queried_session = db.query(DBSession).filter_by(id=session_id).first()
        assert queried_session.agent_id == "support_agent"
        assert len(queried_session.messages) == 2
        assert queried_session.messages[0].role == "user"
        assert queried_session.messages[1].role == "assistant"
        assert queried_session.messages[1].tokens_used == 15
    
    def test_cascade_delete_session_deletes_messages(self, sqlite_memory_db):
        """Test that deleting a session cascades to delete messages."""
        db = sqlite_memory_db
        session_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())
        
        # Create session, message
        session = DBSession(id=session_id, agent_id="test_agent")
        msg = Message(id=msg_id, session_id=session_id, role="user", content="Hi")
        db.add(session)
        db.add(msg)
        db.commit()
        
        # Verify message exists
        existing_msg = db.query(Message).filter_by(id=msg_id).first()
        assert existing_msg is not None
        
        # Delete session
        session_to_delete = db.query(DBSession).filter_by(id=session_id).first()
        db.delete(session_to_delete)
        db.commit()
        
        # Message should be gone too (due to cascade)
        remaining_msg = db.query(Message).filter_by(id=msg_id).first()
        assert remaining_msg is None
    
    def test_api_key_with_agent_id(self, sqlite_memory_db):
        """Test creating an API key restricted to an agent ID."""
        db = sqlite_memory_db
        key = APIKey.generate_key()
        
        api_key = APIKey(
            id=str(uuid.uuid4()),
            agent_id="restricted_agent",
            name="Key 1",
            key_hash=APIKey.hash_key(key),
            is_active=True
        )
        db.add(api_key)
        db.commit()
        
        queried_key = db.query(APIKey).filter_by(agent_id="restricted_agent").first()
        assert queried_key.verify_key(key)
        assert queried_key.agent_id == "restricted_agent"
