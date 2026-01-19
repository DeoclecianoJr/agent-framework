"""Chat interaction endpoints.

Endpoints for sending messages to agents and retrieving chat history.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.models import Session as SessionModel, Message, Agent as AgentModel
from app.core.schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
    ChatRequest,
    ChatResponse,
    MessageListResponse,
    MessageResponse,
)
from app.core.dependencies import get_db, get_executor
from ai_framework.core.executor import AgentExecutor
from ai_framework.agent import AgentRegistry
from app.core.metrics import AGENT_EXECUTION_COUNT, TOKEN_USAGE, CHAT_COST
from app.core.ratelimit import cost_limiter

router = APIRouter(prefix="/chat", tags=["chat"])




@router.post("/", response_model=SessionResponse, status_code=201)
def start_chat(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Start a new chat session with an agent.
    
    Creates a new session for interacting with a specific agent.
    The agent must exist in the database.
    
    Args:
        request: Chat start request with agent_id (slug), optional title/metadata
        db: Database session
        
    Returns:
        Created session with ID, timestamps
        
    Raises:
        404: Agent not found
    """
    # Verify agent exists in database
    agent = db.query(AgentModel).filter(AgentModel.id == request.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{request.agent_id}' not found")
    
    session = SessionModel(
        id=str(uuid.uuid4()),
        agent_id=request.agent_id,
        attrs=request.metadata or {},
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Map attrs -> metadata for response
    return SessionResponse(
        id=session.id,
        agent_id=session.agent_id,
        title=getattr(session, 'title', None),
        metadata=session.attrs,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Get a chat session by ID.
    
    Retrieves session details including metadata.
    
    Args:
        session_id: Session ID to retrieve
        db: Database session
        
    Returns:
        Session data
        
    Raises:
        404: Session not found
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Map attrs -> metadata for response
    return SessionResponse(
        id=session.id,
        agent_id=session.agent_id,
        title=getattr(session, 'title', None),
        metadata=session.attrs,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/{session_id}/messages", response_model=MessageListResponse)
def get_chat_history(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    """Get chat message history for a session.
    
    Retrieves all messages in a session, paginated.
    
    Args:
        session_id: Session ID
        limit: Maximum number of messages (1-1000, default 100)
        offset: Number of messages to skip (default 0)
        db: Database session
        
    Returns:
        List of messages with pagination info
        
    Raises:
        404: Session not found
    """
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    total = db.query(Message).filter(Message.session_id == session_id).count()
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return MessageListResponse(
        messages=messages,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{session_id}/message", response_model=ChatResponse, status_code=201)
async def send_message(
    session_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    executor: AgentExecutor = Depends(get_executor),
) -> ChatResponse:
    """Send a message to an agent in a chat session.
    
    Sends a user message to the agent and returns the response.
    
    Args:
        session_id: Chat session ID
        request: Message content and metadata
        db: Database session
        executor: Agent execution engine
        
    Returns:
        Chat response with user message and agent response
        
    Raises:
        404: Session not found
    """
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Simple rate limiting before execution
    cost_limiter.check_and_inc(session_id)
    
    # Save user message

    user_message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    
    # Get history for context (last 10 messages for now)
    history_objs = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    # Reverse to get chronological order
    history = [{"role": m.role, "content": m.content} for m in reversed(history_objs)]

    # 3. Initialize Guardrails from Agent Config if present
    agent = session.agent
    guardrail_processor = None
    if agent.config and "guardrails" in agent.config:
        from ai_framework.core.guardrails import GuardrailProcessor
        guardrail_processor = GuardrailProcessor.from_config(agent.config)

    # 4. Execute agent
    exec_result = await executor.execute(
        session_id=session_id,
        message_content=request.message,
        history=history,
        guardrails=guardrail_processor,
        system_prompt=agent.config.get("system_prompt") if agent.config else None
    )
    
    # Record metrics
    agent_id = session.agent_id
    usage = exec_result["metadata"].get("usage", {})
    model = exec_result["metadata"].get("model", "unknown")
    
    AGENT_EXECUTION_COUNT.labels(agent_name=agent_id, status="success").inc()
    if usage:
        TOKEN_USAGE.labels(agent_name=agent_id, model=model, token_type="prompt").inc(usage.get("prompt_tokens", 0))
        TOKEN_USAGE.labels(agent_name=agent_id, model=model, token_type="completion").inc(usage.get("completion_tokens", 0))
        cost = usage.get("cost", 0.0)
        CHAT_COST.labels(agent_name=agent_id, model=model).inc(cost)
        
        # Update rate limiter with actual cost (we already registered a $0 hit at the start)
        # In a more advanced version, we'd subtract the initial estimate if we had one.
        if cost > 0:
            cost_limiter.history[session_id][-1] = (cost_limiter.history[session_id][-1][0], cost)

    # Save agent response


    agent_message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=exec_result["content"],
        attrs=exec_result.get("metadata", {}),
        tokens_used=exec_result.get("metadata", {}).get("total_tokens")
    )
    db.add(agent_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(agent_message)
    
    return ChatResponse(
        user_message=MessageResponse.model_validate(user_message),
        agent_message=MessageResponse.model_validate(agent_message),
    )


@router.get("/", response_model=SessionListResponse)
def list_chat_sessions(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    """List all chat sessions with pagination.
    
    Retrieves user's chat sessions.
    
    Args:
        limit: Maximum number of sessions (1-1000, default 100)
        offset: Number of sessions to skip (default 0)
        db: Database session
        
    Returns:
        List of sessions with pagination info
    """
    total = db.query(SessionModel).count()
    sessions = db.query(SessionModel).offset(offset).limit(limit).all()
    
    # Map attrs -> metadata for each session
    session_responses = [
        SessionResponse(
            id=s.id,
            agent_id=s.agent_id,
            title=getattr(s, 'title', None),
            metadata=s.attrs,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]
    
    return SessionListResponse(
        sessions=session_responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/{session_id}", status_code=204)
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Delete a chat session and all associated messages.
    
    Args:
        session_id: Session ID to delete
        db: Database session
        
    Raises:
        404: Session not found
    """
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return None
