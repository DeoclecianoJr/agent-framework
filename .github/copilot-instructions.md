# GitHub Copilot Development Instructions

## Project: AI Agent Framework MVP (Weeks 1-4)

This document defines the development workflow and standards for the AI Agent Framework project. Follow this guide when implementing new features or tasks.

---

## Overview: SDK + Runtime API

**Architecture:**
- **SDK** (`ai_framework/`): Python package with decorators, abstractions, tools
- **Runtime API** (`app/`): FastAPI server to execute agents and handle chat/interaction
- **Database**: Store sessions, messages, and execution history (not agent configs)

---

## 1. Development Flow Overview

### Phases
- **Week 1 (Foundation)**: ✅ Project setup, database, migrations, authentication, logging
- **Week 2 (Core Features)**: SDK core (decorators, LLM abstraction), Chat API endpoints
- **Week 3 (Advanced)**: Agent executor, memory strategies, tool system
- **Week 4 (Polish)**: Optimization, documentation, deployment prep

### For Each Task
1. Create implementation files (`app/`, `app/core/`, `app/api/`)
2. Create comprehensive test file (`tests/test_*.py`)
3. Run full test suite (`pytest tests/ -v`)
4. Verify no test regressions
5. Update task status in planning artifacts
6. Document manual testing requirements

---

## 2. Code Standards

### File Organization

**SDK Package** (`ai_framework/`):
```
ai_framework/
├── __init__.py          # Public API exports
├── decorators.py        # @agent, @tool decorators
├── agent.py             # Agent class
├── core/
│   ├── llm.py           # LLM provider abstraction
│   ├── memory.py        # Memory strategies
│   ├── tools.py         # Tool system
│   └── executor.py      # Agent execution engine
└── integrations/        # LangChain, Anthropic, etc.
```

**Runtime API** (`app/`):
```
app/
├── main.py              # FastAPI application setup
├── core/
│   ├── models.py        # SQLAlchemy (Session, Message, ToolCall)
│   ├── security.py      # Security functions
│   ├── logging.py       # Structured logging
│   ├── schemas.py       # Pydantic validation
│   └── dependencies.py  # Dependency injection
├── api/                 # API endpoints
│   ├── __init__.py      # Export all routers
│   ├── health.py        # Health check
│   ├── chat.py          # Chat/interaction endpoints
│   └── admin.py         # Admin utilities
└── middleware/          # Custom middlewares
    ├── auth.py
    └── trace.py

tests/
├── test_scaffold.py     # Project structure validation
├── test_models.py       # ORM model tests
├── test_auth.py         # Authentication tests
├── test_health_logging.py  # Health & logging tests
├── test_chat_api.py     # Chat endpoint tests
└── test_sdk/            # SDK-specific tests
    ├── test_decorators.py
    ├── test_agent.py
    └── test_tools.py
```

1. **Never define routes directly in `main.py`**
   - `main.py` should ONLY contain: app initialization, middleware registration, router inclusion
   - All endpoint logic must be in `app/api/` modules

2. **Separate routes by domain using APIRouter**
   ```python
   # ❌ BAD - Routes in main.py
   @app.get("/chat")
   def chat():
       pass
   
   # ✅ GOOD - Routes in app/api/chat.py
   from fastapi import APIRouter
   router = APIRouter(prefix="/chat", tags=["chat"])
   
   @router.post("/")
   def chat():
       pass
   ```

3. **API Routes (for Runtime Interaction)**
   - `/chat/*` → `app/api/chat.py` (send messages to agent)
   - `/health` → `app/api/health.py` (status check)
   - `/admin/*` → `app/api/admin.py` (API keys, config)

4. **Register routers in main.py**
   ```python
   from app.api import health_router, admin_router, agents_router
   
   app.include_router(health_router)
   app.include_router(admin_router)
   app.include_router(agents_router)
   ```

5. **Benefits of this approach**
   - **Scalability**: Easy to add new endpoints without cluttering main.py
   - **Maintainability**: Changes to one domain don't affect others
   - **Testability**: Routers can be tested independently
   - **Team collaboration**: Multiple developers can work on different domains
   - **Clear responsibility**: Each file has a single, clear purpose

### Import Standards
- Use absolute imports: `from app.core.models import Agent`
- Group imports: stdlib → third-party → local
- Never use relative imports in app code

### Type Hints
- All functions must have type hints
- Use `Optional[T]` for nullable fields
- Use `List[T]`, `Dict[K, V]` from `typing`

### Docstrings
- Use Google-style docstrings
- Include Args, Returns, Raises sections
- Example:
```python
def create_agent(db: Session, name: str) -> Agent:
    """Create a new agent.
    
    Args:
        db: Database session
        name: Agent name
        
    Returns:
        Created Agent instance
        
    Raises:
        ValueError: If name is empty
    """
```

---

## 3. Testing Requirements

### Test Structure for Each Task
```python
# tests/test_<feature>.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.models import Base

# Fixtures
@pytest.fixture
def sqlite_memory_db():
    """Create in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(sqlite_memory_db):
    """Create FastAPI test client with DB override."""
    from app.main import app, get_db
    app.dependency_overrides[get_db] = lambda: sqlite_memory_db
    yield TestClient(app)
    app.dependency_overrides.clear()

# Test Classes
class TestFeatureUnit:
    """Unit tests for core logic."""
    def test_function_behavior(self):
        ...

class TestFeatureIntegration:
    """Integration tests with database."""
    def test_create_and_query(self, sqlite_memory_db):
        ...

class TestFeatureAPI:
    """API endpoint tests."""
    def test_endpoint_status_code(self, client):
        ...
```

### Test Requirements Per Task
- **Unit Tests**: Test isolated functions, models, utilities (70% of tests)
- **Integration Tests**: Test with real database, queries (20% of tests)
- **E2E Tests**: Test full workflows, API endpoints (10% of tests)
- **Minimum Coverage**: 80% code coverage per module

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_models.py -v

# With coverage
pytest --cov=app tests/

# Specific test class
pytest tests/test_auth.py::TestAPIKeySecurity -v
```

### Expected Test Results
- No failed tests before completing a task
- All existing tests must still pass (no regressions)
- New tests must be meaningful and test behavior, not just coverage

---

## 4. Week 1 Tasks - Foundation (COMPLETED ✅)

### Task 1.1: Initialize Project from Cookiecutter
**Status**: ✅ Complete (3 tests)

**Deliverables**:
- FastAPI application in `app/main.py`
- SQLAlchemy ORM setup in `app/core/models.py`
- Alembic migration system in `alembic/`
- pytest configuration in `pytest.ini`

**Tests**:
- `test_scaffold_files_exist()` - Verify directory structure
- `test_import_app_main()` - Import app without errors
- `test_health_endpoint_smoke()` - /health returns 200 with db/llm status

---

### Task 1.2: Database Schema (Initial Models)
**Status**: ✅ Complete (17 tests)

**Models to Create** in `app/core/models.py`:
- `Agent` (id, name, description, config, created_at, updated_at)
- `Session` (id, agent_id, title, metadata, created_at, updated_at)
- `Message` (id, session_id, role, content, created_at)
- `APIKey` (id, name, key_hash, is_active, created_at, last_used_at)
- `ToolCall` (id, session_id, tool_name, arguments, result, created_at)

**Test Coverage**:
- Model field presence and types
- Relationships (FK constraints)
- Default values and timestamps
- Model creation and querying
- Cascade delete behavior

**Key Implementation Details**:
- Use `datetime.utcnow()` for timestamp defaults (SQLite compatible)
- Use UUID for primary keys: `Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))`
- Add `__tablename__` and `__repr__` to each model
- Implement verify/check methods where needed

---

### Task 1.3: Alembic Migrations
**Status**: ✅ Complete (8 tests)

**Setup**:
- Configure `alembic.ini` with `path_separator = os`
- Create initial migration: `alembic revision --autogenerate -m "Initial migration"`
- Test migration up/down cycles

**Tests**:
- Migration generates without errors
- Migration applies to test database
- Migration can be downgraded
- Schema matches model definitions
- Multiple migrations work sequentially

---

### Task 1.4: API Key Middleware & Authentication
**Status**: ✅ Complete (10 tests)

**Implementation** in `app/core/security.py`:
- `generate_api_key()` - Create 256-bit random key (hex-encoded)
- `hash_api_key(key)` - SHA-256 hash for storage
- `verify_api_key_against_hash(key, hash)` - Verify key matches hash
- `verify_api_key_in_db(db, key)` - Find and validate key in database

**Implementation** in `app/middleware.py`:
- `APIKeyMiddleware` - Validate X-API-Key header on all protected routes
- Skip paths: /health, /openapi.json, /docs, /redoc, /admin/*
- Return 401 if key missing on protected routes

**Endpoints** in `app/main.py`:
- `POST /admin/api-keys` - Generate new API key (returns raw key once)
- `GET /admin/verify-key` - Test endpoint to verify key validity

**Security Notes**:
- Never store plaintext API keys
- Raw key only shown on creation
- Use strong hashing (SHA-256 minimum)
- Implement last_used_at tracking

---

### Task 1.5: Health Check & Basic Logging
**Status**: ✅ Complete (19 tests)

**Implementation** in `app/core/logging.py`:
- `JSONFormatter` - Format logs as JSON with timestamp, level, message, trace_id
- `setup_logging(level)` - Configure application logging
- `trace_id_var` - ContextVar for request correlation
- `set_trace_id()` / `get_trace_id()` - Get/set trace_id in context

**Implementation** in `app/middleware_trace.py`:
- `TraceIDMiddleware` - Generate/propagate trace_id per request
- Read X-Trace-ID from request header or generate UUID
- Add X-Trace-ID to response headers

**Enhanced Endpoint** in `app/main.py`:
- `GET /health` - Check DB and LLM status
  - Returns: `{db: "ok"|"error", llm: "ok"|"error"}`
  - Tests database connectivity with SELECT 1
  - LLM status mocked as "ok" for MVP

**Logging Integration**:
- All logs include trace_id for distributed tracing
- JSON format with: timestamp, level, message, logger, trace_id, exception (if any)
- Setup logging in app startup

**Tests**:
- trace_id generation and propagation
- JSON log format validation
- Health endpoint status codes and responses
- Logging setup and configuration
- Full request flow with logging

---

## 5. Week 2 Tasks - Core Features (TODO)

### Task 2.1: Pydantic Schemas & Validation
**Deliverables**:
- `app/core/schemas.py` - Request/response models
- Chat schemas: ChatRequest, ChatResponse, MessageResponse
- Session schemas: CreateSessionRequest, SessionResponse
- Message schemas: CreateMessageRequest, MessageResponse
- Pagination: PaginationParams, MessageListResponse
- Validation: required fields, string length, enums

**Tests**:
- Valid schema validation passes
- Invalid payloads return 400 with error details
- OpenAPI schema generated correctly
- Field constraints enforced

### Task 2.2: Chat API Endpoints
**Deliverables**:
- `app/api/chat.py` - POST/GET chat endpoints
- POST /chat - Send message to agent (creates/uses session)
- GET /chat/{session_id} - Get session history
- Return 201 on create, 404 on not found
- Require API key on all endpoints

**Tests**:
- Chat endpoints return correct status codes
- Messages persist in DB
- 404 on missing session
- 401 without API key

### Task 2.3: SDK Decorators
**Deliverables**:
- `ai_framework/decorators.py` - @agent, @tool decorators
- `ai_framework/agent.py` - Agent class
- Support function decoration with metadata
- Basic validation and registration

**Tests**:
- Decorator registration works
- Metadata is preserved
- Multiple agents can coexist
- Decorator validation

### Task 2.4: LLM Abstraction Layer
**Deliverables**:
- `ai_framework/core/llm.py` - LLM provider abstraction
- Support multiple providers (OpenAI, Anthropic, Ollama)
- Implement async client for LLM calls
- Token counting interface

**Tests**:
- LLM provider selection
- Async chat completion
- Token counting
- Error handling

### Task 2.5: Memory Strategies (STUB)
**Deliverables**:
- `ai_framework/core/memory.py` - Memory management strategies
- Implement: BufferMemory interface
- Stub implementations for: SummaryMemory, VectorMemory

**Tests**:
- Memory initialization
- Message storage/retrieval
- Interface contracts

### Task 2.6: Tool System (STUB)
**Deliverables**:
- `ai_framework/core/tools.py` - Tool abstraction and registry
- Tool class and registry
- Stub implementations: web_search, calculator

**Tests**:
- Tool invocation interface
- Tool registration
- Error handling contract

---

## 6. Week 3 Tasks - Advanced Features (TODO)

### Task 3.1: Agent Executor
**Deliverables**:
- `ai_framework/core/executor.py` - Agent execution engine
- Execute agents with tools and context
- Handle function calling and tool resolution
- Stream responses in real-time

**Tests**:
- Agent execution flow
- Tool invocation and results
- Error handling and recovery

### Task 3.2: Memory Integration
**Deliverables**:
- Complete `ai_framework/core/memory.py` implementations
- SummaryMemory, BufferMemory, VectorMemory
- Memory pruning and summarization

**Tests**:
- Memory retrieval respects limits
- Summarization reduces tokens
- Context preservation

### Task 3.3: Tool System Implementation
**Deliverables**:
- Complete `ai_framework/core/tools.py`
- Built-in tools: web_search, calculator, python_repl
- Tool execution and error handling

**Tests**:
- Tool invocation
- Output formatting
- Error handling

### Task 3.4-3.6: Extended features (observability, config, etc.)

---

## 7. Week 4 Tasks - Polish & Deployment (TODO)

### Task 4.1-4.4: Finalize and prepare for production

---

## 8. Development Checklist for Each Task

Before marking a task as complete:

- [ ] **Code Implementation**
  - [ ] All required files created/modified
  - [ ] Type hints on all functions
  - [ ] Docstrings with examples
  - [ ] No commented-out code
  - [ ] Imports organized and minimal

- [ ] **Testing**
  - [ ] Unit tests written (70% of tests)
  - [ ] Integration tests written (20% of tests)
  - [ ] E2E tests written (10% of tests)
  - [ ] All new tests passing
  - [ ] No regression in existing tests
  - [ ] Test coverage ≥ 80% for new modules

- [ ] **Code Quality**
  - [ ] No linting errors (flake8, black)
  - [ ] Type checking passes (mypy)
  - [ ] No security issues (bandit)
  - [ ] Follows project standards

- [ ] **Documentation**
  - [ ] Docstrings complete
  - [ ] README updated if needed
  - [ ] Task status in planning artifacts updated
  - [ ] Example usage documented

- [ ] **Testing (Manual - REQUIRED)**
  - [ ] See Section 9 below

---

## 9. Manual Testing Requirements (BEFORE TASK COMPLETION)

### ⚠️ IMPORTANT: Manual Testing by Human Developer

**Before marking ANY task as complete, a human developer MUST perform the following manual tests:**

### For API-Based Tasks (Tasks 1.4, 1.5, 2.2, etc.)

**Test Setup**:
```bash
# Start the development server
.venv/bin/uvicorn app.main:app --reload

# In another terminal, run tests
.venv/bin/pytest tests/test_<feature>.py -v
```

**Manual Verification Checklist**:
- [ ] Server starts without errors
- [ ] All tests pass (green checkmark)
- [ ] Test coverage meets threshold (≥80%)
- [ ] No deprecation warnings (except accepted SQLAlchemy datetime)
- [ ] API endpoints respond with correct status codes
- [ ] Error responses include helpful error messages
- [ ] Database schema matches current models (alembic status clean)

### For Authentication/Middleware Tasks

**Test with curl**:
```bash
# Test endpoint without authentication
curl http://localhost:8000/admin/verify-key
# Should return: 400 Bad Request

# Generate API key
RESPONSE=$(curl -X POST http://localhost:8000/admin/api-keys)
API_KEY=$(echo $RESPONSE | grep -o '"api_key":"[^"]*' | cut -d'"' -f4)

# Test with valid API key
curl -H "X-API-Key: $API_KEY" http://localhost:8000/health
# Should return: 200 OK with {db: ok, llm: ok}

# Test health endpoint without API key (should pass - no auth required)
curl http://localhost:8000/health
# Should return: 200 OK with {db: ok, llm: ok}
```

### For Logging/Observability Tasks

**Test JSON logging output**:
```bash
# Check that logs are valid JSON with trace_id
.venv/bin/uvicorn app.main:app --reload 2>&1 | grep "trace_id"
# Should see: {..., "trace_id": "uuid", ...}

# Verify trace_id propagation across requests
curl -H "X-Trace-ID: test-123" http://localhost:8000/health
# Check response header: X-Trace-ID: test-123
# Check logs: trace_id matches
```

### For Database/Schema Tasks

**Test migrations**:
```bash
# Check current migration status
alembic current
# Should show: Latest migration applied

# Test downgrade/upgrade cycle
alembic downgrade -1
alembic upgrade +1
# Both commands should succeed

# Verify database schema
sqlite3 test.db ".schema"
# Should match all defined models
```

### For CRUD Endpoint Tasks

**Test complete workflow**:
```bash
# Create resource
curl -X POST http://localhost:8000/admin/api-keys
# Should return: 201 Created with resource ID

# Retrieve resource
curl -H "X-API-Key: <key>" http://localhost:8000/agents/<id>
# Should return: 200 OK with resource data

# Update resource
curl -X PUT http://localhost:8000/agents/<id> -d '{"name": "updated"}'
# Should return: 200 OK with updated data

# Delete resource
curl -X DELETE http://localhost:8000/agents/<id>
# Should return: 204 No Content

# Verify deletion
curl http://localhost:8000/agents/<id>
# Should return: 404 Not Found
```

### After Manual Testing

When ALL manual tests pass:
1. ✅ Mark task as **COMPLETE** in planning artifacts
2. ✅ Record manual test results (date, environment)
3. ✅ Note any issues encountered and how they were resolved
4. ✅ Commit code with message: `feat: Task X.Y - <description>`

### If Manual Tests Fail

1. ❌ Do NOT mark task complete
2. ❌ Debug using error messages and logs
3. ❌ Make code fixes and re-run unit/integration tests
4. ❌ Repeat manual testing until all tests pass
5. ❌ Document what was broken and the fix

---

## 10. Git Workflow

### Commit Messages
Format: `<type>: <subject>`

Examples:
```
feat: Task 1.4 - API key authentication with middleware
fix: Health endpoint returns correct status format
test: Add 19 tests for health check and logging
docs: Update Task 1.5 documentation
```

### Before Pushing
```bash
# Run full test suite
pytest tests/ -v --tb=short

# Check for linting (if configured)
# flake8 app/

# Check types (if mypy configured)
# mypy app/

# View what will be committed
git diff --staged
```

---

## 11. Debugging Guide

### Common Issues

**Issue: Tests fail with "no such table"**
- Cause: Fixtures not creating database tables
- Solution: Ensure `Base.metadata.create_all()` called in fixture
- Check: `from app.core.models import Base`

**Issue: API endpoint returns 500**
- Solution: Check server logs for exception traceback
- Verify: Required environment variables set
- Test: Database connectivity works

**Issue: Middleware not working**
- Solution: Verify middleware registered in `main.py` with `app.add_middleware()`
- Order matters: Register TraceID before APIKey middleware
- Test: With curl to see response headers

**Issue: Tests pass locally but fail in CI**
- Check: Database file persists across tests (use in-memory)
- Check: Environment variable differences
- Solution: Use fixtures with `yield` for cleanup

---

## 12. Performance Considerations

### Database
- Index frequently queried fields (agent.name, session.agent_id)
- Use eager loading for relationships in API responses
- Implement pagination for list endpoints (limit 100)

### API
- Add caching headers to cacheable responses
- Implement rate limiting on admin endpoints
- Use async/await for I/O operations

### Logging
- JSON logging has minimal overhead
- Use appropriate log levels (not DEBUG in production)
- Archive logs to prevent disk growth

---

## 13. Security Best Practices

### Authentication
- Always validate API keys against hash, never plaintext
- Use secure random generation (`secrets` module)
- Implement key expiration and rotation

### Database
- Use parameterized queries (SQLAlchemy ORM handles this)
- Never log sensitive data (passwords, keys)
- Validate all user input with Pydantic

### API
- Set security headers (CORS, CSP, etc.)
- Validate Content-Type headers
- Implement request size limits
- Log all authentication failures

---

## 14. Resources & References

### Project Structure
- **Plan**: `_bmad-output/planning-artifacts/tasks-with-test-scope.md`
- **Architecture**: `_bmad-output/planning-artifacts/architecture.md`
- **Status**: `_bmad-output/planning-artifacts/tasks/` (per-task details)

### Documentation
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Pydantic**: https://docs.pydantic.dev/
- **Pytest**: https://docs.pytest.org/

### Testing Tools
- **pytest**: Test runner and assertions
- **TestClient**: FastAPI testing client
- **SQLAlchemy in-memory DB**: `sqlite:///:memory:`
- **caplog**: Pytest fixture for log capture

---

## 15. Questions & Support

For clarifications on:
- **Architecture**: Check `_bmad-output/planning-artifacts/architecture.md`
- **Requirements**: Check `_bmad-output/planning-artifacts/prd.md`
- **Test Scope**: Check specific task file in `_bmad-output/planning-artifacts/tasks/`
- **Code Style**: Reference existing implementations in Week 1 tasks

---

**Last Updated**: 2026-01-16  
**Created By**: Development Team  
**Status**: Active - Following Week 1 completion
