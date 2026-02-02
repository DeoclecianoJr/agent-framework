"""
Message Repository - Database operations for conversation messages.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.repositories.base import BaseRepository
from app.core.models import Message


class MessageRepository(BaseRepository[Message, dict, dict]):
    """Repository for message-related database operations."""
    
    def __init__(self):
        super().__init__(Message)
    
    def get_by_session(
        self, 
        db: Session, 
        session_id: str, 
        limit: int = 100,
        order: str = "asc"
    ) -> List[Message]:
        """Get messages by session ID with ordering."""
        query = db.query(self.model).filter(self.model.session_id == session_id)
        
        if order == "desc":
            query = query.order_by(desc(self.model.created_at))
        else:
            query = query.order_by(asc(self.model.created_at))
            
        return query.limit(limit).all()
    
    def create_message(
        self, 
        db: Session, 
        session_id: str, 
        role: str, 
        content: str,
        metadata: dict = None
    ) -> Message:
        """Create a new message in a session."""
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    def get_recent_context(
        self, 
        db: Session, 
        session_id: str, 
        limit: int = 10
    ) -> List[Message]:
        """Get recent messages for context window."""
        return (
            db.query(self.model)
            .filter(self.model.session_id == session_id)
            .order_by(desc(self.model.created_at))
            .limit(limit)
            .all()
        )