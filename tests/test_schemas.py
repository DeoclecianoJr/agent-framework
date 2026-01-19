"""Tests for Pydantic schemas and validation (Task 2.1)."""
import pytest
from datetime import datetime
from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.models import Base
from app.core.schemas import (
    CreateAgentRequest,
    UpdateAgentRequest,
    AgentResponse,
    CreateSessionRequest,
    SessionResponse,
    CreateMessageRequest,
    MessageResponse,
    CreateAPIKeyRequest,
    APIKeyCreateResponse,
    ChatRequest,
    PaginationParams,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sqlite_memory_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    
    yield SessionLocal()
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def override_get_db(sqlite_memory_db):
    """Provide database override for FastAPI dependency injection."""
    def _get_db():
        try:
            yield sqlite_memory_db
        finally:
            pass
    return _get_db


@pytest.fixture
def client(override_get_db):
    """Create FastAPI test client with database override."""
    from app.main import app
    from app.core.dependencies import get_db
    
    # Clear any existing overrides
    app.dependency_overrides.clear()
    
    # Set database override
    app.dependency_overrides[get_db] = override_get_db
    
    yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


# ============================================================================
# Tests - Agent Schemas
# ============================================================================


class TestAgentSchemas:
    """Test Agent schema validation."""

    def test_create_agent_valid(self):
        """Verify valid CreateAgentRequest passes validation."""
        agent = CreateAgentRequest(
            name="Test Agent",
            description="A test agent",
            config={"model": "gpt-4"}
        )
        assert agent.name == "Test Agent"
        assert agent.description == "A test agent"
        assert agent.config["model"] == "gpt-4"

    def test_create_agent_minimal(self):
        """Verify CreateAgentRequest works with minimal fields."""
        agent = CreateAgentRequest(name="Minimal Agent")
        assert agent.name == "Minimal Agent"
        assert agent.description is None
        assert agent.config == {}

    def test_create_agent_empty_name_fails(self):
        """Verify empty name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateAgentRequest(name="")
        
        errors = exc_info.value.errors()
        assert any("name" in str(err["loc"]) for err in errors)

    def test_create_agent_whitespace_name_fails(self):
        """Verify whitespace-only name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateAgentRequest(name="   ")
        
        errors = exc_info.value.errors()
        assert any("name" in str(err["loc"]) for err in errors)

    def test_create_agent_missing_name_fails(self):
        """Verify missing name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateAgentRequest()
        
        errors = exc_info.value.errors()
        assert any("name" in str(err["loc"]) for err in errors)

    def test_create_agent_name_too_long_fails(self):
        """Verify name exceeding max length raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateAgentRequest(name="a" * 256)
        
        errors = exc_info.value.errors()
        assert any("name" in str(err["loc"]) for err in errors)

    def test_update_agent_partial(self):
        """Verify UpdateAgentRequest allows partial updates."""
        update = UpdateAgentRequest(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.description is None
        assert update.config is None

    def test_update_agent_all_none(self):
        """Verify UpdateAgentRequest allows all fields None."""
        update = UpdateAgentRequest()
        assert update.name is None
        assert update.description is None
        assert update.config is None


# ============================================================================
# Tests - Session Schemas
# ============================================================================


class TestSessionSchemas:
    """Test Session schema validation."""

    def test_create_session_valid(self):
        """Verify valid CreateSessionRequest passes validation."""
        session = CreateSessionRequest(
            agent_id="agent-123",
            title="Test Session",
            metadata={"user_id": "user-456"}
        )
        assert session.agent_id == "agent-123"
        assert session.title == "Test Session"
        assert session.metadata["user_id"] == "user-456"

    def test_create_session_minimal(self):
        """Verify CreateSessionRequest works with minimal fields."""
        session = CreateSessionRequest(agent_id="agent-123")
        assert session.agent_id == "agent-123"
        assert session.title is None
        assert session.metadata == {}

    def test_create_session_missing_agent_id_fails(self):
        """Verify missing agent_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateSessionRequest()
        
        errors = exc_info.value.errors()
        assert any("agent_id" in str(err["loc"]) for err in errors)


# ============================================================================
# Tests - Message Schemas
# ============================================================================


class TestMessageSchemas:
    """Test Message schema validation."""

    def test_create_message_valid(self):
        """Verify valid CreateMessageRequest passes validation."""
        message = CreateMessageRequest(
            session_id="session-123",
            role="user",
            content="Hello, world!"
        )
        assert message.session_id == "session-123"
        assert message.role == "user"
        assert message.content == "Hello, world!"

    def test_create_message_invalid_role_fails(self):
        """Verify invalid role raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateMessageRequest(
                session_id="session-123",
                role="invalid_role",
                content="Test"
            )
        
        errors = exc_info.value.errors()
        assert any("role" in str(err["loc"]) for err in errors)

    def test_create_message_empty_content_fails(self):
        """Verify empty content raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateMessageRequest(
                session_id="session-123",
                role="user",
                content=""
            )
        
        errors = exc_info.value.errors()
        assert any("content" in str(err["loc"]) for err in errors)

    def test_create_message_valid_roles(self):
        """Verify all valid roles pass validation."""
        valid_roles = ["user", "assistant", "system", "tool"]
        
        for role in valid_roles:
            message = CreateMessageRequest(
                session_id="session-123",
                role=role,
                content="Test content"
            )
            assert message.role == role


# ============================================================================
# Tests - API Key Schemas
# ============================================================================


class TestAPIKeySchemas:
    """Test API Key schema validation."""

    def test_create_api_key_valid(self):
        """Verify valid CreateAPIKeyRequest passes validation."""
        request = CreateAPIKeyRequest(
            name="Production Key",
            agent_id="agent-123"
        )
        assert request.name == "Production Key"
        assert request.agent_id == "agent-123"

    def test_create_api_key_minimal(self):
        """Verify CreateAPIKeyRequest works without agent_id."""
        request = CreateAPIKeyRequest(name="Test Key")
        assert request.name == "Test Key"
        assert request.agent_id is None

    def test_create_api_key_empty_name_fails(self):
        """Verify empty name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateAPIKeyRequest(name="")
        
        errors = exc_info.value.errors()
        assert any("name" in str(err["loc"]) for err in errors)

    def test_create_api_key_whitespace_name_fails(self):
        """Verify whitespace-only name raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateAPIKeyRequest(name="   ")
        
        errors = exc_info.value.errors()
        assert any("name" in str(err["loc"]) for err in errors)


# ============================================================================
# Tests - Chat Schemas
# ============================================================================


class TestChatSchemas:
    """Test Chat schema validation."""

    def test_chat_request_valid(self):
        """Verify valid ChatRequest passes validation."""
        request = ChatRequest(
            message="Hello, agent!",
            session_id="session-123"
        )
        assert request.message == "Hello, agent!"
        assert request.session_id == "session-123"

    def test_chat_request_no_session_id(self):
        """Verify ChatRequest works without session_id."""
        request = ChatRequest(message="Hello!")
        assert request.message == "Hello!"
        assert request.session_id is None

    def test_chat_request_empty_message_fails(self):
        """Verify empty message raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="")
        
        errors = exc_info.value.errors()
        assert any("message" in str(err["loc"]) for err in errors)

    def test_chat_request_whitespace_message_fails(self):
        """Verify whitespace-only message raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="   ")
        
        errors = exc_info.value.errors()
        assert any("message" in str(err["loc"]) for err in errors)

    def test_chat_request_message_too_long_fails(self):
        """Verify message exceeding max length raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(message="a" * 10001)
        
        errors = exc_info.value.errors()
        assert any("message" in str(err["loc"]) for err in errors)


# ============================================================================
# Tests - Pagination Schemas
# ============================================================================


class TestPaginationSchemas:
    """Test Pagination schema validation."""

    def test_pagination_defaults(self):
        """Verify PaginationParams has correct defaults."""
        params = PaginationParams()
        assert params.limit == 100
        assert params.offset == 0

    def test_pagination_custom_values(self):
        """Verify PaginationParams accepts custom values."""
        params = PaginationParams(limit=50, offset=10)
        assert params.limit == 50
        assert params.offset == 10

    def test_pagination_limit_too_small_fails(self):
        """Verify limit < 1 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(limit=0)
        
        errors = exc_info.value.errors()
        assert any("limit" in str(err["loc"]) for err in errors)

    def test_pagination_limit_too_large_fails(self):
        """Verify limit > 1000 raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(limit=1001)
        
        errors = exc_info.value.errors()
        assert any("limit" in str(err["loc"]) for err in errors)

    def test_pagination_negative_offset_fails(self):
        """Verify negative offset raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(offset=-1)
        
        errors = exc_info.value.errors()
        assert any("offset" in str(err["loc"]) for err in errors)


# ============================================================================
# Tests - API Validation Integration
# ============================================================================


class TestAPIValidation:
    """Test API endpoint validation with Pydantic schemas."""

    def test_create_api_key_with_invalid_payload_returns_422(self, client):
        """Verify POST /admin/api-keys with empty payload returns 422."""
        response = client.post("/admin/api-keys", json={})
        assert response.status_code == 422  # FastAPI returns 422 for validation errors
        
        data = response.json()
        assert "detail" in data

    def test_create_api_key_with_empty_name_returns_422(self, client):
        """Verify POST /admin/api-keys with empty name returns 422."""
        response = client.post("/admin/api-keys", json={"name": ""})
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data

    def test_create_api_key_with_whitespace_name_returns_422(self, client):
        """Verify POST /admin/api-keys with whitespace name returns 422."""
        response = client.post("/admin/api-keys", json={"name": "   "})
        assert response.status_code == 422


# ============================================================================
# Tests - OpenAPI Integration
# ============================================================================


class TestOpenAPIGeneration:
    """Test OpenAPI schema generation."""

    def test_openapi_json_endpoint_exists(self, client):
        """Verify /openapi.json endpoint exists."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_contains_schemas(self, client):
        """Verify OpenAPI includes Pydantic schemas."""
        response = client.get("/openapi.json")
        data = response.json()
        
        assert "components" in data
        assert "schemas" in data["components"]
        
        schemas = data["components"]["schemas"]
        
        # Check for our schemas
        assert "CreateAPIKeyRequest" in schemas
        assert "APIKeyCreateResponse" in schemas

    def test_openapi_contains_endpoints(self, client):
        """Verify OpenAPI includes API endpoints."""
        response = client.get("/openapi.json")
        data = response.json()
        
        assert "paths" in data
        paths = data["paths"]
        
        # Check for our endpoints
        assert "/health" in paths
        assert "/admin/api-keys" in paths
        assert "/admin/verify-key" in paths

    def test_openapi_admin_api_keys_post_definition(self, client):
        """Verify /admin/api-keys POST endpoint is properly defined."""
        response = client.get("/openapi.json")
        data = response.json()
        
        endpoint = data["paths"]["/admin/api-keys"]["post"]
        
        # Check request body
        assert "requestBody" in endpoint
        
        # Check responses
        assert "responses" in endpoint
        assert "201" in endpoint["responses"]

    def test_openapi_validation_error_responses(self, client):
        """Verify OpenAPI includes 422 validation error responses."""
        response = client.get("/openapi.json")
        data = response.json()
        
        endpoint = data["paths"]["/admin/api-keys"]["post"]
        
        # FastAPI automatically adds 422 for validation errors
        assert "422" in endpoint["responses"]
