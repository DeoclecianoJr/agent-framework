"""Chat interaction endpoints.

Endpoints for sending messages to agents and retrieving chat history.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.models import Session as SessionModel, Message
from app.core.cost_monitoring import CostMonitor
from app.schemas import (
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
    ChatRequest,
    ChatResponse,
    MessageListResponse,
    MessageResponse,
)
from app.core.dependencies import get_db, get_executor
from app.core.logging import get_logger
from ai_framework.core.executor import AgentExecutor
from ai_framework.agent import AgentRegistry, AgentDefinition
from app.core.metrics import AGENT_EXECUTION_COUNT, TOKEN_USAGE, CHAT_COST
from app.core.ratelimit import cost_limiter
from app.core.pii import pii_anonymizer  # Import PII Anonymizer
from app.services import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)

# Initialize service
chat_service = ChatService()


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
    try:
        return chat_service.create_session(db=db, request=request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions", response_model=SessionListResponse)
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
    
    # Map database model to response schema
    session_responses = [
        SessionResponse(
            id=s.id,
            agent_id=s.agent_id,
            title=s.attrs.get("title"),  # Get title from attrs JSON field
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
        title=session.attrs.get("title"),  # Get title from attrs JSON field
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
    
    # Mask PII in user message (FR78)
    sanitized_content = pii_anonymizer.mask_text(request.message)

    # Save user message
    user_message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=sanitized_content,
    )
    db.add(user_message)
    
    # 3. Lookup Agent in SDK Registry (Authoritative source for config)
    try:
        from ai_framework.agent import AgentRegistry, AgentDefinition
        agent_def: AgentDefinition = AgentRegistry.instance().get(session.agent_id)
    except KeyError:
        raise HTTPException(
            status_code=404, 
            detail=f"Agent '{session.agent_id}' is not registered in the application SDK."
        )

    # 4. Resolve memory strategy from agent config
    from ai_framework.core.memory import MemoryManager
    memory_strategy = agent_def.config.get("memory_strategy", "buffer")
    
    # Create memory with session's summary from attrs
    session_summary = session.attrs.get("summary") if session.attrs else None
    memory = MemoryManager.create(
        memory_strategy, 
        llm=executor.llm, 
        summary=session_summary
    )
    
    # Load appropriate amount of history based on memory strategy
    if memory_strategy == "summary" and hasattr(memory, 'max_messages'):
        # For SummaryMemory, load recent messages but not too many to avoid constant summarization
        # Load up to max_messages to allow proper threshold detection
        recent_limit = memory.max_messages + 2  # Load slightly more than max to allow detection
        
        # New logic: Skip messages that were already summarized to avoid redundancy
        history_query = db.query(Message).filter(Message.session_id == session_id)
        last_summarized_id = session.attrs.get("last_summarized_id") if session.attrs else None
        
        if last_summarized_id:
            # Only load messages created AFTER the last summarization point
            marker_date = db.query(Message.created_at).filter(Message.id == last_summarized_id).scalar()
            if marker_date:
                logger.info(f"Session {session_id} has summary marker. Loading messages after {marker_date}")
                history_query = history_query.filter(Message.created_at > marker_date)

        history_objs = (
            history_query.order_by(Message.created_at.desc())
            .limit(recent_limit)
            .all()
        )
        history_objs.reverse()  # Restore chronological order
        
        # Load recent messages without triggering summarization
        for msg in history_objs:
            if msg.id == user_message.id:
                continue
            await memory.add_message(msg.role, msg.content, summarize=False)
        
        logger.info(f"Loaded {len(memory.recent_messages)} messages into memory buffer (max: {memory.max_messages})")
    else:
        # For other memory types, load all history
        history_objs = (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        # Load all history messages
        for msg in history_objs:
            if msg.id == user_message.id:
                continue
            await memory.add_message(msg.role, msg.content)
    
    # Attach memory to executor
    executor.memory = memory
    logger.debug(f"Memory attached to executor for session {session_id}. Strategy: {memory_strategy}")

    guardrail_processor = None
    if agent_def.config and "guardrails" in agent_def.config:
        from ai_framework.core.guardrails import GuardrailProcessor
        guardrail_processor = GuardrailProcessor.from_config(agent_def.config)

    # 5. Execute agent with RAG context
    exec_result = await executor.execute(
        session_id=session_id,
        message_content=sanitized_content,
        guardrails=guardrail_processor,
        system_prompt=agent_def.config.get("system_prompt"),
        agent_id=session.agent_id  # ✅ Pass agent_id for RAG integration
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
    usage = exec_result.get("metadata", {}).get("usage", {})
    
    # Store token/cost data in attrs
    metadata = exec_result.get("metadata", {})
    if usage:
        metadata["usage"] = {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "cost": usage.get("cost"),
            "model": usage.get("model")
        }

    agent_message = Message(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=exec_result["content"],
        attrs=metadata,
        tokens_used=usage.get("total_tokens")
    )
    db.add(agent_message)
    
    # Check cost thresholds and log alerts
    cost_monitor = CostMonitor(db)
    message_cost = usage.get("cost", 0.0)
    if message_cost > 0:
        alerts = cost_monitor.check_cost_thresholds(session_id, session.agent_id, message_cost)
        for alert in alerts:
            logger.warning(f"Cost threshold exceeded: {alert.threshold_type} - "
                         f"${alert.current_value:.4f} > ${alert.threshold_value:.4f} "
                         f"(agent: {alert.agent_id}, session: {alert.session_id})")
    
    # Persist summary if it was updated during this execution
    from ai_framework.core.memory import SummaryMemory
    was_summarized = False
    if isinstance(memory, SummaryMemory) and memory.summary_updated:
        was_summarized = True
        logger.info(f"Summarization detected. Updating session {session_id}. Agent message ID: {agent_message.id}")
        # Store summary in attrs JSON field along with last_summarized_id
        session_attrs = dict(session.attrs or {})
        session_attrs["summary"] = memory.summary
        session_attrs["last_summarized_id"] = agent_message.id
        session.attrs = session_attrs
        db.add(session)
        logger.info(f"Session {session_id} updated with summary and last_summarized_id={agent_message.id}")
    
    db.commit()
    db.refresh(user_message)
    db.refresh(agent_message)
    
    # Extract usage data for agent message
    agent_usage = {}
    if agent_message.attrs and 'usage' in agent_message.attrs:
        usage_data = agent_message.attrs['usage']
        agent_usage = {
            'prompt_tokens': usage_data.get('prompt_tokens'),
            'completion_tokens': usage_data.get('completion_tokens'),
            'total_tokens': usage_data.get('total_tokens'),
            'cost': usage_data.get('cost'),
            'model': usage_data.get('model')
        }
    
    # Create MessageResponse with usage data
    agent_msg_response = MessageResponse(
        id=agent_message.id,
        session_id=agent_message.session_id,
        role=agent_message.role,
        content=agent_message.content,
        metadata=agent_message.attrs,
        tokens_used=agent_message.tokens_used,
        created_at=agent_message.created_at,
        **agent_usage  # Include usage data at top level
    )
    
    return ChatResponse(
        user_message=MessageResponse.model_validate(user_message),
        agent_message=agent_msg_response,
        summarized=was_summarized
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
