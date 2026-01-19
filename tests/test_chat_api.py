"""Tests for Chat API endpoints.

Tests for sending messages to agents and retrieving chat history.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.models import Base, Session as SessionModel, Message, Agent as AgentModel
from app.core.dependencies import get_db, TEST_API_KEY
from ai_framework.agent import AgentRegistry
from ai_framework.decorators import agent as agent_decorator

# Database setup
engine = create_engine(
    "sqlite:///./test_chat.db",
    connect_args={"check_same_thread": False}
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    session = TestingSessionLocal()
    
    # Clear all data before test - order matters due to FK
    session.query(Message).delete()
    session.query(SessionModel).delete()
    session.query(AgentModel).delete()
    session.commit()
    
    yield session
    
    session.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with overridden database."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def test_agent(db_session):
    """Register a test agent in the SDK registry and database."""
    registry = AgentRegistry.instance()
    agent_id = "test-agent-1"
    
    # Create in DB
    agent_db = AgentModel(
        id=agent_id,
        name="Test Agent",
        description="A test agent",
        config={}
    )
    db_session.add(agent_db)
    db_session.commit()
    
    # Check if already registered in SDK
    try:
        return registry.get(agent_id)
    except KeyError:
        # Define and register in SDK
        @agent_decorator(name=agent_id, description="A test agent")
        def my_agent(message, history=None):
            return f"Response to {message}"
        return registry.get(agent_id)


class TestStartChat:
    """Test starting a new chat session."""
    
    def test_start_chat_creates_session(self, client, test_agent):
        """Starting chat should create a session with provided agent."""
        response = client.post(
            "/chat/",
            json={"agent_id": test_agent.name},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"] == test_agent.name
        assert "id" in data
        assert "created_at" in data
    
    def test_start_chat_with_metadata(self, client, test_agent):
        """Starting chat with metadata should include it in response."""
        metadata = {"topic": "test", "version": "1.0"}
        response = client.post(
            "/chat/",
            json={"agent_id": test_agent.name, "metadata": metadata},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] == metadata
    
    def test_start_chat_nonexistent_agent(self, client):
        """Starting chat with nonexistent agent should return 404."""
        response = client.post(
            "/chat/",
            json={"agent_id": "nonexistent"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_start_chat_requires_api_key(self, client, test_agent):
        """Starting chat without API key should return 401."""
        response = client.post(
            "/chat/",
            json={"agent_id": test_agent.name}
        )
        assert response.status_code == 401


class TestGetChatSession:
    """Test retrieving chat session details."""
    
    def test_get_chat_session(self, db_session, client, test_agent):
        """Getting chat session should return session details."""
        session = SessionModel(
            id="session-1",
            agent_id=test_agent.name,
            attrs={"topic": "test"}
        )
        db_session.add(session)
        db_session.commit()
        
        response = client.get(
            f"/chat/{session.id}",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session.id
        assert data["agent_id"] == test_agent.name
        assert data["metadata"] == {"topic": "test"}
    
    def test_get_nonexistent_session(self, client):
        """Getting nonexistent session should return 404."""
        response = client.get(
            "/chat/nonexistent",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]
    
    def test_get_session_requires_api_key(self, db_session, client, test_agent):
        """Getting session without API key should return 401."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        response = client.get(f"/chat/{session.id}")
        assert response.status_code == 401


class TestGetChatHistory:
    """Test retrieving chat message history."""
    
    def test_get_chat_history_empty(self, db_session, client, test_agent):
        """Getting history for empty session should return empty list."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        response = client.get(
            f"/chat/{session.id}/messages",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["total"] == 0
    
    def test_get_chat_history_with_messages(self, db_session, client, test_agent):
        """Getting history should return all messages in session."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        # Add messages
        msg1 = Message(
            id="msg-1",
            session_id=session.id,
            role="user",
            content="Hello"
        )
        msg2 = Message(
            id="msg-2",
            session_id=session.id,
            role="assistant",
            content="Hi there"
        )
        db_session.add(msg1)
        db_session.add(msg2)
        db_session.commit()
        
        response = client.get(
            f"/chat/{session.id}/messages",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["total"] == 2
    
    def test_get_chat_history_pagination(self, db_session, client, test_agent):
        """Getting history with pagination should respect limit/offset."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        # Add 10 messages
        for i in range(10):
            msg = Message(
                id=f"msg-{i}",
                session_id=session.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            db_session.add(msg)
        db_session.commit()
        
        # Test limit
        response = client.get(
            f"/chat/{session.id}/messages?limit=5",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 5
        assert data["total"] == 10
        assert data["limit"] == 5
        assert data["offset"] == 0
        
        # Test offset
        response = client.get(
            f"/chat/{session.id}/messages?limit=5&offset=5",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 5
        assert data["offset"] == 5
    
    def test_get_history_nonexistent_session(self, client):
        """Getting history for nonexistent session should return 404."""
        response = client.get(
            "/chat/nonexistent/messages",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404


class TestSendMessage:
    """Test sending messages to an agent."""
    
    def test_send_message(self, db_session, client, test_agent):
        """Sending message should create user and agent messages."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        response = client.post(
            f"/chat/{session.id}/message",
            json={"message": "Hello agent"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_message"]["content"] == "Hello agent"
        assert data["user_message"]["role"] == "user"
        assert "agent_message" in data
        assert data["agent_message"]["role"] == "assistant"
    
    def test_send_message_nonexistent_session(self, client):
        """Sending message to nonexistent session should return 404."""
        response = client.post(
            "/chat/nonexistent/message",
            json={"message": "Hello"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404
    
    def test_send_message_saves_to_database(self, db_session, client, test_agent):
        """Sending message should persist to database."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        response = client.post(
            f"/chat/{session.id}/message",
            json={"message": "Test message"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 201
        
        # Verify messages saved
        messages = db_session.query(Message).filter(
            Message.session_id == session.id
        ).all()
        assert len(messages) == 2  # user + agent
        assert messages[0].content == "Test message"
    
    def test_send_message_requires_api_key(self, db_session, client, test_agent):
        """Sending message without API key should return 401."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        response = client.post(
            f"/chat/{session.id}/message",
            json={"message": "Hello"}
        )
        assert response.status_code == 401


class TestListChatSessions:
    """Test listing chat sessions."""
    
    def test_list_empty_sessions(self, client):
        """Listing sessions when empty should return empty list."""
        response = client.get(
            "/chat/",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0
    
    def test_list_sessions_with_data(self, db_session, client, test_agent):
        """Listing sessions should return all sessions."""
        # Create 3 sessions
        for i in range(3):
            session = SessionModel(
                id=f"session-{i}",
                agent_id=test_agent.name
            )
            db_session.add(session)
        db_session.commit()
        
        response = client.get(
            "/chat/",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 3
        assert data["total"] == 3
    
    def test_list_sessions_pagination(self, db_session, client, test_agent):
        """Listing sessions with pagination should respect limit/offset."""
        # Create 10 sessions
        for i in range(10):
            session = SessionModel(
                id=f"session-{i}",
                agent_id=test_agent.name
            )
            db_session.add(session)
        db_session.commit()
        
        # Test limit
        response = client.get(
            "/chat/?limit=5",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 5
        assert data["total"] == 10
        
        # Test offset
        response = client.get(
            "/chat/?limit=5&offset=5",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 5


class TestDeleteChatSession:
    """Test deleting chat sessions."""
    
    def test_delete_session(self, db_session, client, test_agent):
        """Deleting session should remove it and associated messages."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        response = client.delete(
            f"/chat/{session.id}",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 204
        
        # Verify deletion
        deleted = db_session.query(SessionModel).filter(
            SessionModel.id == session.id
        ).first()
        assert deleted is None
    
    def test_delete_nonexistent_session(self, client):
        """Deleting nonexistent session should return 404."""
        response = client.delete(
            "/chat/nonexistent",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 404
    
    def test_delete_session_requires_api_key(self, db_session, client, test_agent):
        """Deleting session without API key should return 401."""
        session = SessionModel(id="session-1", agent_id=test_agent.name)
        db_session.add(session)
        db_session.commit()
        
        response = client.delete(f"/chat/{session.id}")
        assert response.status_code == 401


class TestChatIntegration:
    """Integration tests for complete chat workflows."""
    
    def test_complete_chat_workflow(self, client, test_agent):
        """Complete workflow: create session, send messages, get history."""
        # Create session
        create_response = client.post(
            "/chat/",
            json={"agent_id": test_agent.name},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert create_response.status_code == 201
        session_id = create_response.json()["id"]
        
        # Send message
        message_response = client.post(
            f"/chat/{session_id}/message",
            json={"message": "Hello"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert message_response.status_code == 201
        
        # Get history
        history_response = client.get(
            f"/chat/{session_id}/messages",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert history_response.status_code == 200
        data = history_response.json()
        assert len(data["messages"]) == 2
        
        # Get session
        session_response = client.get(
            f"/chat/{session_id}",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert session_response.status_code == 200
        assert session_response.json()["id"] == session_id
    
    def test_multiple_sessions_independent(self, client, test_agent, db_session):
        """Multiple sessions should be independent."""
        # Create two sessions
        session1 = client.post(
            "/chat/",
            json={"agent_id": test_agent.name},
            headers={"X-API-Key": TEST_API_KEY}
        ).json()
        session2 = client.post(
            "/chat/",
            json={"agent_id": test_agent.name},
            headers={"X-API-Key": TEST_API_KEY}
        ).json()
        
        # Add messages to session 1
        client.post(
            f"/chat/{session1['id']}/message",
            json={"message": "Message 1"},
            headers={"X-API-Key": TEST_API_KEY}
        )
        
        # Check session 2 is empty
        response = client.get(
            f"/chat/{session2['id']}/messages",
            headers={"X-API-Key": TEST_API_KEY}
        )
        assert response.status_code == 200
        assert len(response.json()["messages"]) == 0
