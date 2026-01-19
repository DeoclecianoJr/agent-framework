"""Administrative endpoints for system management.

Includes API key management, health checks, and system monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import text
from sqlalchemy.orm import Session
import uuid
from typing import List

from app.core.models import APIKey, Agent
from app.core.security import generate_api_key, hash_api_key, verify_api_key_in_db
from app.core.logging import get_logger
from app.core.schemas import (
    CreateAPIKeyRequest, 
    APIKeyCreateResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
    AgentResponse
)
from app.core.dependencies import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=201)
def create_api_key(request: CreateAPIKeyRequest, db: Session = Depends(get_db)):
    """Create a new API key (admin endpoint, no auth required for MVP).
    
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
    from app.main import get_db
    
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
# Agent Management
# ============================================================================

@router.post("/agents", response_model=AgentResponse, status_code=201)
def create_agent(request: CreateAgentRequest, db: Session = Depends(get_db)):
    """Create a new agent in the system.
    
    Args:
        request: Agent creation data
        db: Database session
    """
    # Check if agent with same name/id already exists to prevent duplicates
    # For MVP we use name as ID if it looks like a slug, or just random UUID
    agent_id = request.name.lower().replace(" ", "-") # Simple slug
    
    existing = db.query(Agent).filter(Agent.id == agent_id).first()
    if existing:
        # If slug exists, add a suffix
        agent_id = f"{agent_id}-{str(uuid.uuid4())[:8]}"
        
    agent = Agent(
        id=agent_id,
        name=request.name,
        description=request.description,
        config=request.config or {}
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/agents", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """List all agents in the system."""
    return db.query(Agent).all()


@router.get("/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent details."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, request: UpdateAgentRequest, db: Session = Depends(get_db)):
    """Update agent configuration."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if request.name is not None:
        agent.name = request.name
    if request.description is not None:
        agent.description = request.description
    if request.config is not None:
        # Deep merge or just overwrite? For MVP just overwrite config root
        agent.config = request.config
        
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}", status_code=204)
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    """Delete an agent and its sessions."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(agent)
    db.commit()
    return None
