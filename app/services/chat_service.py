"""
Chat Service - Business logic for chat operations.

Handles the orchestration of chat requests, including:
- Session management
- Message processing
- LLM integration
- Cost tracking
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.repositories import SessionRepository, MessageRepository
from app.schemas import ChatRequest, ChatResponse, CreateSessionRequest, SessionResponse
from app.core.cost_monitoring import CostMonitor
from app.core.models import Agent

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat-related business logic."""
    
    def __init__(self):
        self.session_repo = SessionRepository()
        self.message_repo = MessageRepository()
    
    def create_session(self, db: Session, request: CreateSessionRequest) -> SessionResponse:
        """Create a new chat session."""
        try:
            # Validate agent exists
            agent = db.query(Agent).filter(Agent.id == request.agent_id).first()
            if not agent:
                raise ValueError(f"Agent {request.agent_id} not found")
            
            # Create session
            session = self.session_repo.create_session(
                db=db,
                agent_id=request.agent_id,
                title=request.title
            )
            
            logger.info(f"Created session {session.id} for agent {request.agent_id}")
            
            return SessionResponse(
                id=session.id,
                agent_id=session.agent_id,
                title=session.attrs.get("title"),  # Get title from attrs JSON field
                metadata=session.attrs,
                created_at=session.created_at,
                updated_at=session.updated_at
            )
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def process_chat(self, db: Session, request: ChatRequest) -> ChatResponse:
        """Process a chat message and generate response."""
        try:
            # Get or create session
            if request.session_id:
                session = self.session_repo.get(db, request.session_id)
                if not session:
                    raise ValueError(f"Session {request.session_id} not found")
            else:
                # Create new session (needs agent_id in request)
                session = self.session_repo.create_session(
                    db=db,
                    agent_id="support_pro",  # Default agent
                    title="New Chat"
                )
            
            # Save user message
            user_message = self.message_repo.create_message(
                db=db,
                session_id=session.id,
                role="user",
                content=request.message
            )
            
            # Get conversation context
            context = self.message_repo.get_recent_context(
                db=db,
                session_id=session.id,
                limit=10
            )
            
            # Generate AI response (placeholder)
            ai_response = self._generate_ai_response(context, request.message)
            
            # Save AI message
            ai_message = self.message_repo.create_message(
                db=db,
                session_id=session.id,
                role="assistant",
                content=ai_response
            )
            
            # Track costs
            cost_monitor = CostMonitor(db)
            cost = cost_monitor.calculate_request_cost(
                input_tokens=len(request.message.split()),
                output_tokens=len(ai_response.split()),
                model="gpt-4o-mini"
            )
            
            logger.info(f"Processed chat for session {session.id}, cost: ${cost}")
            
            return ChatResponse(
                message=ai_response,
                session_id=session.id,
                cost=cost,
                message_id=ai_message.id
            )
            
        except Exception as e:
            logger.error(f"Failed to process chat: {e}")
            raise
    
    def _generate_ai_response(self, context: list, message: str) -> str:
        """Generate AI response (placeholder for LLM integration)."""
        # This is where you'd integrate with OpenAI, Claude, etc.
        # For now, return a simple response
        return f"Echo: {message} (from chat service)"
    
    def get_session_messages(
        self, 
        db: Session, 
        session_id: str, 
        limit: int = 100
    ) -> list:
        """Get all messages for a session."""
        return self.message_repo.get_by_session(
            db=db,
            session_id=session_id,
            limit=limit
        )