"""
Session Repository - Database operations for conversation sessions.
"""
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.repositories.base import BaseRepository
from app.core.models import Session as SessionModel
from app.schemas import CreateSessionRequest


class SessionRepository(BaseRepository[SessionModel, CreateSessionRequest, dict]):
    """Repository for session-related database operations."""
    
    def __init__(self):
        super().__init__(SessionModel)
    
    def get_by_agent(self, db: Session, agent_id: str, limit: int = 100) -> List[SessionModel]:
        """Get sessions by agent ID, ordered by most recent."""
        return (
            db.query(self.model)
            .filter(self.model.agent_id == agent_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
            .all()
        )
    
    def get_active_sessions(self, db: Session, limit: int = 100) -> List[SessionModel]:
        """Get active sessions across all agents."""
        return (
            db.query(self.model)
            .filter(self.model.is_active == True)
            .order_by(desc(self.model.updated_at))
            .limit(limit)
            .all()
        )
    
    def create_session(self, db: Session, agent_id: str, title: str = None) -> SessionModel:
        """Create a new conversation session."""
        session_data = {
            "id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "user_id": None,
            "attrs": {"title": title or "New Conversation"}  # Store title in attrs JSON field
        }
        
        session = SessionModel(**session_data)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session