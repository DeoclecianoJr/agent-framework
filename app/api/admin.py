"""Administrative endpoints for system management.

Includes API key management, health checks, system monitoring, and guardrails configuration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import text
from sqlalchemy.orm import Session
import uuid
import json
from typing import List, Dict, Any, Optional

from app.core.models import APIKey, AuditLog
from app.core.security import generate_api_key, hash_api_key, verify_api_key_in_db
from app.core.logging import get_logger
from app.core.audit import log_audit_event
from app.schemas import (
    CreateAPIKeyRequest, 
    APIKeyCreateResponse,
    GuardrailConfigRequest,
    GuardrailConfigResponse,
    ToolRestrictionsResponse,
    AuditLogResponse
)
from app.core.dependencies import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=201)
def create_api_key(request: CreateAPIKeyRequest, db: Session = Depends(get_db)):
    """Create a new API key (admin endpoint, no auth required for MVP).
    
    Requires JSON body with name field:
    - {"name": "My API Key", "agent_id": "support_pro"}
    
    Args:
        request: API key creation request with name and optional agent_id
        db: Database session
    
    Returns:
        APIKeyCreateResponse with raw key (shown only once)
    """
    key_id = str(uuid.uuid4())
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    
    api_key = APIKey(
        id=key_id,
        name=request.name,
        agent_id=request.agent_id,
        key_hash=key_hash,
        is_active=True
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    # Audit log
    log_audit_event(
        db,
        event_type="create_api_key",
        event_data={
            "key_id": api_key.id,
            "name": api_key.name,
            "agent_id": api_key.agent_id
        },
        actor="admin"
    )
    
    logger.info(f"Created API key: {api_key.id} (name: {api_key.name})")
    
    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        agent_id=api_key.agent_id,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        key=raw_key,  # Raw key only shown on creation
        key_hash=api_key.key_hash,
    )


@router.get("/verify-key")
def verify_key(x_api_key: str = Header(None), db: Session = Depends(lambda: None)):
    """Verify if an API key is valid (for testing).
    
    Header: X-API-Key (the raw key to verify)
    """
    # Import here to avoid circular dependency
    from app.core.dependencies import get_db
    
    # Get actual database session
    if db is None:
        db = next(get_db())
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-API-Key header required"
        )
    
    verified = verify_api_key_in_db(db, x_api_key)
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    return {
        "valid": True,
        "key_id": verified.id,
        "is_active": verified.is_active
    }


# ============================================================================
# Guardrails Configuration Endpoints
# ============================================================================

# In-memory guardrail storage for MVP (would be database in production)
_guardrail_configs: Dict[str, Dict[str, Any]] = {}


@router.post("/guardrails/{agent_id}", response_model=GuardrailConfigResponse)
def configure_guardrails(
    agent_id: str, 
    config: GuardrailConfigRequest,
    db: Session = Depends(get_db)
):
    """Configure guardrails for a specific agent.
    
    Args:
        agent_id: ID of the agent to configure
        config: Guardrail configuration
        db: Database session
        
    Returns:
        Updated guardrail configuration
    """
    from datetime import datetime
    
    # Get current config or create new
    current = _guardrail_configs.get(agent_id, {})
    
    # Update only provided fields
    if config.blocklist is not None:
        current["blocklist"] = config.blocklist
    if config.allowlist is not None:
        current["allowlist"] = config.allowlist
    if config.min_confidence is not None:
        current["min_confidence"] = config.min_confidence
    if config.allowed_themes is not None:
        current["allowed_themes"] = config.allowed_themes
    if config.tool_restrictions is not None:
        current["tool_restrictions"] = config.tool_restrictions
    
    current["updated_at"] = datetime.now()
    _guardrail_configs[agent_id] = current
    
    logger.info(f"Updated guardrail config for agent {agent_id}: {len(current)} settings")
    
    return GuardrailConfigResponse(
        agent_id=agent_id,
        blocklist=current.get("blocklist", []),
        allowlist=current.get("allowlist", []),
        min_confidence=current.get("min_confidence", 0.0),
        allowed_themes=current.get("allowed_themes", []),
        tool_restrictions=current.get("tool_restrictions", {}),
        updated_at=current["updated_at"]
    )


@router.get("/guardrails/{agent_id}", response_model=GuardrailConfigResponse)
def get_guardrail_config(agent_id: str, db: Session = Depends(get_db)):
    """Get current guardrail configuration for an agent.
    
    Args:
        agent_id: ID of the agent
        db: Database session
        
    Returns:
        Current guardrail configuration
    """
    from datetime import datetime
    
    config = _guardrail_configs.get(agent_id, {})
    
    if not config:
        # Return default configuration
        config = {
            "blocklist": [],
            "allowlist": [],
            "min_confidence": 0.0,
            "allowed_themes": [],
            "tool_restrictions": {},
            "updated_at": datetime.now()
        }
    
    return GuardrailConfigResponse(
        agent_id=agent_id,
        blocklist=config.get("blocklist", []),
        allowlist=config.get("allowlist", []),
        min_confidence=config.get("min_confidence", 0.0),
        allowed_themes=config.get("allowed_themes", []),
        tool_restrictions=config.get("tool_restrictions", {}),
        updated_at=config.get("updated_at", datetime.now())
    )


@router.get("/guardrails/{agent_id}/tools", response_model=ToolRestrictionsResponse)
def get_agent_tool_restrictions(agent_id: str, db: Session = Depends(get_db)):
    """Get tool restrictions for a specific agent.
    
    Args:
        agent_id: ID of the agent
        db: Database session
        
    Returns:
        Tool restrictions information
    """
    # Check all configurations for tool restrictions (global search)
    all_tool_restrictions = {}
    has_any_restrictions = False
    
    for config in _guardrail_configs.values():
        restrictions = config.get("tool_restrictions", {})
        all_tool_restrictions.update(restrictions)
        if restrictions:
            has_any_restrictions = True
    
    # Check agent-specific restrictions first
    allowed_tools = None
    
    if agent_id in all_tool_restrictions:
        allowed_tools = all_tool_restrictions[agent_id]
    elif "*" in all_tool_restrictions:
        allowed_tools = all_tool_restrictions["*"]
    
    return ToolRestrictionsResponse(
        agent_id=agent_id,
        allowed_tools=allowed_tools,
        has_restrictions=has_any_restrictions
    )


@router.delete("/guardrails/{agent_id}")
def delete_guardrail_config(agent_id: str, db: Session = Depends(get_db)):
    """Delete guardrail configuration for an agent.
    
    Args:
        agent_id: ID of the agent
        db: Database session
        
    Returns:
        Success confirmation
    """
    if agent_id in _guardrail_configs:
        del _guardrail_configs[agent_id]
        logger.info(f"Deleted guardrail config for agent {agent_id}")
        return {"message": f"Guardrail configuration deleted for agent {agent_id}"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No guardrail configuration found for agent {agent_id}"
    )


@router.get("/guardrails", response_model=List[GuardrailConfigResponse])
def list_all_guardrail_configs(db: Session = Depends(get_db)):
    """List all guardrail configurations.
    
    Args:
        db: Database session
        
    Returns:
        List of all guardrail configurations
    """
    from datetime import datetime
    
    configs = []
    for agent_id, config in _guardrail_configs.items():
        configs.append(GuardrailConfigResponse(
            agent_id=agent_id,
            blocklist=config.get("blocklist", []),
            allowlist=config.get("allowlist", []),
            min_confidence=config.get("min_confidence", 0.0),
            allowed_themes=config.get("allowed_themes", []),
            tool_restrictions=config.get("tool_restrictions", {}),
            updated_at=config.get("updated_at", datetime.now())
        ))
    
    return configs


@router.get("/stats")
def get_system_stats(db: Session = Depends(get_db)):
    """Get system-wide usage statistics (admins only)."""
    from sqlalchemy import func, desc
    from datetime import datetime, timezone, timedelta
    from app.core.models import Message, Session as SessionModel
    
    try:
        # Total messages, tokens and cost
        total_messages = db.query(func.count(Message.id)).scalar() or 0
        total_cost = db.query(func.sum(Message.cost)).scalar() or 0.0
        total_tokens = db.query(func.sum(Message.tokens_used)).scalar() or 0
        
        # Messages by agent (grouping by agent_id in sessions)
        messages_by_agent = db.query(
            SessionModel.agent_id,
            func.count(Message.id).label('message_count'),
            func.sum(Message.cost).label('total_cost'),
            func.sum(Message.tokens_used).label('total_tokens')
        ).join(
            Message, SessionModel.id == Message.session_id
        ).group_by(SessionModel.agent_id).all()
        
        # Messages by model
        messages_by_model = db.query(
            Message.model,
            func.count(Message.id).label('message_count'),
            func.sum(Message.cost).label('total_cost'),
            func.sum(Message.tokens_used).label('total_tokens')
        ).filter(
            Message.model.isnot(None)
        ).group_by(Message.model).all()
        
        # Recent activity (last 24h)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_messages = db.query(func.count(Message.id)).filter(
            Message.created_at >= yesterday
        ).scalar() or 0
        
        # Active sessions
        active_sessions = db.query(func.count(SessionModel.id)).scalar() or 0
        
        return {
            "summary": {
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "total_cost_usd": round(float(total_cost), 4),
                "active_sessions": active_sessions,
                "recent_messages_24h": recent_messages
            },
            "agents": [
                {
                    "agent_id": agent_id,
                    "message_count": count,
                    "total_tokens": tokens or 0,
                    "total_cost_usd": round(float(cost or 0), 4)
                }
                for agent_id, count, cost, tokens in messages_by_agent
            ],
            "models": [
                {
                    "model": model,
                    "message_count": count,
                    "total_tokens": tokens or 0,
                    "total_cost_usd": round(float(cost or 0), 4)
                }
                for model, count, cost, tokens in messages_by_model
            ],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate stats: {str(e)}"
        )

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = 100, 
    offset: int = 0, 
    event_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Retrieve audit logs (admin only).
    
    Args:
        limit: Max number of logs to return
        offset: Pagination offset
        event_type: Filter by event type
        db: Database session
        
    Returns:
        List of audit log entries
    """
    query = db.query(AuditLog)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    # Sort by timestamp descending (newest first)
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset).all()
