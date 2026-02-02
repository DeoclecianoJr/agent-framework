"""
Database models for AI Agent Framework.

Models:
- Session: Represents a conversation session with an agent
- Message: Represents individual messages in a session
- APIKey: Represents API credentials for access
- ToolCall: Represents tool invocations during execution
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    Boolean,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector
import hashlib
import secrets
import uuid

Base = declarative_base()


class Agent(Base):
    """
    Represents an agent definition.
    """
    __tablename__ = "agents"
    
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Session(Base):
    """
    Represents a conversation session with an agent.
    
    Attributes:
        id: Unique session identifier (UUID)
        agent_id: Reference to the internal agent (matched in AgentRegistry)
        user_id: External user identifier (optional)
        attrs: JSON metadata (user context, external references, etc.)
        created_at: Timestamp of creation
        updated_at: Timestamp of last interaction
    """
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(255), ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    attrs = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")



class Message(Base):
    """
    Represents a single message in a session conversation.
    
    Attributes:
        id: Unique message identifier (UUID)
        session_id: Foreign key to Session
        role: Message role ("user", "assistant", "system")
        content: Message text content
        attrs: JSON metadata (tool calls, confidence scores, citations, etc.)
        tokens_used: Token count for LLM calls
        created_at: Timestamp of creation
    """
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    attrs = Column(JSON, nullable=False, default={})
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    
    # Relationships
    session = relationship("Session", back_populates="messages")
    tool_calls = relationship("ToolCall", back_populates="message", cascade="all, delete-orphan")


class APIKey(Base):
    """
    Represents API credentials for access.
    
    Attributes:
        id: Unique key identifier (UUID)
        agent_id: Optional agent ID restriction (from SDK registry)
        name: Human-readable key name
        key_hash: SHA-256 hash of the actual API key (never store plaintext)
        is_active: Whether the key can be used
        created_at: Timestamp of creation
        last_used_at: Timestamp of last successful use
        expires_at: Optional expiration timestamp
    """
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(255), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 = 64 hex chars
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key using SHA-256."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new random API key (32 bytes = 256 bits)."""
        return secrets.token_hex(32)
    
    def verify_key(self, key: str) -> bool:
        """Verify if provided key matches stored hash."""
        return self.key_hash == self.hash_key(key)


class ToolCall(Base):
    """
    Represents a tool invocation during agent execution.
    
    Attributes:
        id: Unique call identifier (UUID)
        message_id: Foreign key to Message (the assistant message that triggered the call)
        tool_name: Name of the tool invoked
        input_args: JSON-serialized input arguments
        output: Tool execution output (JSON)
        status: Execution status (pending, success, error)
        error_message: Error details if status is error
        execution_time_ms: How long the tool took to execute
        created_at: Timestamp of invocation
    """
    __tablename__ = "tool_calls"
    
    id = Column(String(36), primary_key=True)
    message_id = Column(String(36), ForeignKey("messages.id"), nullable=False, index=True)
    tool_name = Column(String(255), nullable=False, index=True)
    input_args = Column(JSON, nullable=False, default={})
    output = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending, success, error
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    
    # Relationships
    message = relationship("Message", back_populates="tool_calls")


class AuditLog(Base):
    """
    Represents an audit entry for security-critical actions.
    
    Attributes:
        id: Unique identifier (UUID)
        event_type: Type of event (e.g., "create_api_key", "update_guardrails")
        actor: Who performed the action (e.g., system, user_ip, admin)
        metadata: Details about the event (JSON)
        timestamp: When the event occurred
    """
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(100), nullable=False, index=True)
    actor = Column(String(255), nullable=True)  # IP or User ID if available
    event_data = Column(JSON, nullable=False, default={})
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)


class KnowledgeDocument(Base):
    """
    Represents a document chunk with vector embeddings for RAG.
    
    Attributes:
        id: Unique identifier (UUID)
        agent_id: Reference to agent (for knowledge isolation)
        source_type: Type of source ('google_drive', 'sharepoint', 'manual')
        source_id: File ID from Drive/SharePoint API
        file_name: Original file name
        content_chunk: Text content of this chunk
        chunk_index: Position of chunk in original document
        embedding: Vector embedding (384 dimensions for all-MiniLM-L6-v2 local model)
        attrs: JSONB with page_number, folder_path, last_modified, etc.
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "knowledge_documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(255), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(255), nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    content_chunk = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    embedding = Column(Vector(384), nullable=True)  # all-MiniLM-L6-v2 local embeddings (384 dimensions)
    attrs = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class KnowledgeSource(Base):
    """
    Represents a configured knowledge source for an agent.
    
    Attributes:
        id: Unique identifier (UUID)
        agent_id: Reference to agent
        source_type: Type of source ('google_drive', 'sharepoint')
        config: JSONB with folder_id, site_url, access_token_encrypted, refresh_token_encrypted
        last_sync_at: Timestamp of last successful sync
        next_sync_at: Timestamp of next scheduled sync
        sync_status: Current sync status ('pending', 'running', 'completed', 'failed')
        sync_errors: JSONB with error details if sync failed
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "knowledge_sources"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(255), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False, default={})
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    next_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(50), nullable=False, default="pending")
    sync_errors = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

