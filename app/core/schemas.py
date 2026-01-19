"""Pydantic schemas for request/response validation.

Provides data validation, serialization, and OpenAPI schema generation.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# Agent Schemas
# ============================================================================


class AgentBase(BaseModel):
    """Base schema for Agent with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(None, max_length=1000, description="Agent description")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent configuration (LLM settings, prompts, etc.)")


class CreateAgentRequest(AgentBase):
    """Request schema for creating a new agent."""
    
    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Agent name cannot be empty or whitespace")
        return v.strip()


class UpdateAgentRequest(BaseModel):
    """Request schema for updating an agent."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    config: Optional[Dict[str, Any]] = None
    
    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Agent name cannot be empty or whitespace")
        return v.strip() if v else v


class AgentResponse(AgentBase):
    """Response schema for agent data."""
    
    id: str = Field(..., description="Unique agent ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Session Schemas
# ============================================================================


class SessionBase(BaseModel):
    """Base schema for Session with common fields."""
    
    title: Optional[str] = Field(None, max_length=500, description="Session title")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Session metadata"
    )


class CreateSessionRequest(SessionBase):
    """Request schema for creating a new session."""
    
    agent_id: str = Field(..., description="ID of the agent for this session")


class SessionResponse(SessionBase):
    """Response schema for session data.
    
    Maps ORM 'attrs' field to schema 'metadata' field for API contract.
    """
    
    id: str = Field(..., description="Unique session ID")
    agent_id: str = Field(..., description="Associated agent ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Message Schemas
# ============================================================================


class MessageBase(BaseModel):
    """Base schema for Message with common fields."""
    
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., min_length=1, description="Message content")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Ensure role is valid."""
        allowed_roles = {'user', 'assistant', 'system', 'tool'}
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v


class CreateMessageRequest(MessageBase):
    """Request schema for creating a new message."""
    
    session_id: str = Field(..., description="ID of the session for this message")


class MessageResponse(MessageBase):
    """Response schema for message data."""
    
    id: str = Field(..., description="Unique message ID")
    session_id: str = Field(..., description="Associated session ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="attrs", description="Message metadata (tool calls, tokens, etc.)")
    tokens_used: Optional[int] = Field(None, description="Tokens used for this message")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ============================================================================
# API Key Schemas
# ============================================================================


class CreateAPIKeyRequest(BaseModel):
    """Request schema for creating a new API key."""
    
    name: str = Field(..., min_length=1, max_length=255, description="API key name/label")
    agent_id: Optional[str] = Field(None, description="Optional agent ID to associate with key")
    
    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("API key name cannot be empty or whitespace")
        return v.strip()


class APIKeyResponse(BaseModel):
    """Response schema for API key data (without the raw key)."""
    
    id: str = Field(..., description="Unique API key ID")
    name: str = Field(..., description="API key name")
    agent_id: Optional[str] = Field(None, description="Associated agent ID")
    is_active: bool = Field(..., description="Whether key is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(APIKeyResponse):
    """Response schema for API key creation (includes raw key once)."""
    
    key: str = Field(..., description="Raw API key (shown only on creation)")
    key_hash: str = Field(..., description="Hashed API key (for reference)")


# ============================================================================
# Tool Call Schemas
# ============================================================================


class ToolCallBase(BaseModel):
    """Base schema for ToolCall with common fields."""
    
    tool_name: str = Field(..., min_length=1, max_length=255, description="Name of the tool")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")


class CreateToolCallRequest(ToolCallBase):
    """Request schema for creating a tool call record."""
    
    session_id: str = Field(..., description="ID of the session")


class ToolCallResponse(ToolCallBase):
    """Response schema for tool call data."""
    
    id: str = Field(..., description="Unique tool call ID")
    session_id: str = Field(..., description="Associated session ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Chat/Execution Schemas
# ============================================================================


class ChatRequest(BaseModel):
    """Request schema for chat/agent execution."""
    
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    session_id: Optional[str] = Field(None, description="Existing session ID (creates new if not provided)")
    
    @field_validator('message')
    @classmethod
    def validate_message_not_empty(cls, v: str) -> str:
        """Ensure message is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v.strip()


class ChatResponse(BaseModel):
    """Response schema for chat interaction.
    
    Contains both the user message sent and the agent response received.
    """
    
    user_message: MessageResponse = Field(..., description="User message that was sent")
    agent_message: MessageResponse = Field(..., description="Agent response message")


# ============================================================================
# Pagination & List Schemas
# ============================================================================


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")


class AgentListResponse(BaseModel):
    """Response schema for list of agents."""
    
    agents: List[AgentResponse] = Field(..., description="List of agents")
    total: int = Field(..., description="Total count of agents")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class SessionListResponse(BaseModel):
    """Response schema for list of sessions."""
    
    sessions: List[SessionResponse] = Field(..., description="List of sessions")
    total: int = Field(..., description="Total count of sessions")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class MessageListResponse(BaseModel):
    """Response schema for list of messages."""
    
    messages: List[MessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total count of messages")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


# ============================================================================
# Error Response Schemas
# ============================================================================


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    loc: Optional[List[str]] = Field(None, description="Error location (field path)")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    detail: str = Field(..., description="Error description")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Validation errors")
