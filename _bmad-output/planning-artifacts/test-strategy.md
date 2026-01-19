---
documentType: 'test-strategy'
project_name: 'AI Agent Framework'
user_name: 'Wbj-compassuol-010'
date: '2026-01-13'
status: 'Pre-Implementation Phase'
totalFRs: 90
totalNFRs: 37
targetCoverage: '≥80%'
testFramework: 'pytest + pytest-asyncio + pytest-cov'
---

# Test Strategy & Test Case Specifications

_Comprehensive testing plan created BEFORE implementation to ensure requirements clarity and testability-first design._

---

## 1. Testing Philosophy & Approach

### Development Methodology

**Hybrid TDD + BDD Approach:**

- **TDD (Test-Driven Development):** For core business logic and utilities
  - Write failing test first (Red)
  - Implement minimum code to pass (Green)
  - Refactor while keeping tests green (Refactor)
  - Focus: Models, LLM abstraction, memory strategies, token counting

- **BDD (Behavior-Driven Development):** For user-facing features and workflows
  - Define behavior in Gherkin scenarios (Given/When/Then)
  - Implement step definitions with pytest-bdd
  - Validate from user perspective
  - Focus: Chat flows, tool execution, session management, API endpoints

**Benefits:**
- TDD ensures reliable, well-tested internals
- BDD validates that features meet user requirements
- Combined approach provides comprehensive coverage

### Testing Pyramid

```
                    /\
                   /  \
                  / E2E \ (5-10% of tests)
                 /______\
                /        \
               / Integr.  \ (20-30% of tests)
              /____________\
            /              \
           /    Unit Tests   \ (60-70% of tests)
          /____________________\
```

### Coverage Targets

- **Overall Coverage:** ≥80% code coverage
- **Critical Paths:** 100% (authentication, data persistence, LLM integration)
- **Business Logic:** ≥90% (agent execution, tool processing)
- **Infrastructure:** ≥70% (logging, error handling, rate limiting)
- **API Endpoints:** 100% (all routes + happy/error paths)

### Testing Types

1. **Unit Tests** (fastest, most isolated)
   - Individual functions/classes
   - Mock external dependencies
   - Database mocking with SQLAlchemy test fixtures
   - Run on every save (watch mode)

2. **Integration Tests** (moderate complexity)
   - Component interactions
   - Real database (test instance)
   - Mock external APIs (LLM, web services)
   - Test repository interactions
   - Run on commit

3. **End-to-End Tests** (full workflow)
   - Complete chat flow: request → agent → LLM → response
   - Tool execution with real tool implementations
   - Memory persistence and retrieval
   - Error scenarios and recovery
   - Run pre-deployment

4. **Performance Tests** (regression prevention)
   - Agent response time < 3s (simple), < 15s (complex)
   - API latency < 500ms (excluding LLM)
   - Memory usage per agent < 500MB
   - Database query performance

### Mocking Strategy

**What to Mock:**
- LLM API calls (OpenAI, Anthropic) → use LangChain's `FakeListChatModel` and `FakeLLM`
- External web services (web_search, weather) → use pytest-mock fixtures
- Time-dependent operations → use freezegun
- Async operations → use pytest-asyncio
- Callbacks for token tracking → mock callback handlers

**What NOT to Mock:**
- Database operations → use test database
- Error handling logic → test real exceptions
- Authentication/authorization → test real flow
- Logging → capture and assert

---

## 2. Test Organization & Structure

### Directory Structure

```
ai_framework/
├── app/
│   ├── api/
│   │   ├── chat.py              # Chat interaction endpoints
│   │   ├── health.py            # Health check endpoint
│   │   ├── admin.py             # Admin utilities (API keys)
│   │   ├── middleware/
│   │   │   └── auth.py
│   │   └── dependencies.py
│   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── security.py
│   ├── llm/
│   │   ├── abstraction.py
│   │   ├── provider.py
│   │   └── token_counter.py
│   └── observability/
│       ├── logging.py
│       └── tracing.py
│
├── ai_framework/              # SDK Package
│   ├── __init__.py
│   ├── decorators.py          # @agent, @tool decorators
│   ├── agent.py               # Agent class
│   ├── core/
│   │   ├── llm.py
│   │   ├── memory.py
│   │   ├── tools.py
│   │   └── executor.py
│   └── integrations/
│
├── tests/
│   ├── conftest.py                    # Shared fixtures
│   ├── features/                       # BDD scenarios (pytest-bdd)
│   │   ├── chat_workflow.feature       # User chat scenarios
│   │   ├── tool_execution.feature      # Tool usage scenarios
│   │   ├── memory_management.feature   # Memory strategies
│   │   │── step_defs/                  # Step definitions
│   │       ├── chat_steps.py
│   │       ├── tool_steps.py
│   │       └── memory_steps.py
│   ├── unit/
│   │   ├── test_api/
│   │   │   ├── test_chat.py           # Test chat API routes
│   │   │   ├── test_health.py         # Test health endpoint
│   │   │   ├── test_admin.py          # Test admin endpoints
│   │   │   └── middleware/
│   │   │       └── test_auth.py       # Test authentication
│   │   ├── test_core/
│   │   │   ├── test_models.py         # Test SQLAlchemy models
│   │   │   ├── test_schemas.py        # Test Pydantic schemas
│   │   │   └── test_security.py       # Test security functions
│   │   ├── test_sdk/
│   │   │   ├── test_decorators.py     # Test @agent, @tool decorators
│   │   │   ├── test_agent.py          # Test Agent class
│   │   │   ├── test_memory.py         # Test memory strategies
│   │   │   └── test_executor.py       # Test agent execution
│   │   ├── test_llm/
│   │   │   ├── test_abstraction.py    # LLM interface
│   │   │   ├── test_provider.py       # Provider switching
│   │   │   └── test_token_counter.py
│   │   └── test_observability/
│   │       ├── test_logging.py
│   │       └── test_tracing.py
│   │
│   ├── integration/
│   │   ├── test_api/
│   │   │   └── test_chat_workflow.py  # Full chat workflow
│   │   ├── test_sdk/
│   │   │   ├── test_agent_with_memory.py
│   │   │   └── test_agent_with_tools.py
│   │   ├── test_tools/
│   │   │   └── test_tool_execution.py
│   │   └── test_llm/
│   │       └── test_provider_switching.py
│   │
│   ├── e2e/
│   │   ├── test_chat_start_to_finish.py  # Full workflow from session creation to chat
│   │   ├── test_chat_with_tools.py       # Agent uses multiple tools
│   │   ├── test_memory_persistence.py    # Full session lifecycle
│   │   └── test_error_scenarios.py       # Error handling end-to-end
│   │
│   ├── performance/
│   │   ├── test_response_time.py      # < 3s / < 15s requirements
│   │   ├── test_api_latency.py        # < 500ms excluding LLM
│   │   ├── test_memory_usage.py       # < 500MB per agent
│   │   └── test_concurrent_calls.py   # 100+ concurrent
│   │
│   ├── fixtures/
│   │   ├── database.py                # DB fixtures
│   │   ├── models.py                  # SQLAlchemy model fixtures
│   │   ├── llm.py                     # LLM mock fixtures
│   │   ├── agents.py                  # Test agent fixtures
│   │   ├── sessions.py                # Test session fixtures
│   │   ├── tools.py                   # Test tool fixtures
│   │   └── data.py                    # Test data factories
│   │
│   └── utils/
│       ├── assertions.py              # Custom assertions
│       ├── builders.py                # Test object builders
│       └── factories.py               # Factory patterns for test data

tests/
├── pytest.ini                         # pytest configuration
├── .env.test                          # Test environment variables
└── conftest.py                        # Global fixtures + configuration
```

### Naming Conventions

**Test Files:**
- `test_<module>.py` - Unit tests for module
- `test_<module>_<feature>.py` - Specific feature tests
- Mirrors source structure: `tests/unit/api/test_agents.py` matches `app/api/routes/agents.py`

**Test Functions:**
- `test_<feature>_<scenario>_<expected>()` 
- Examples:
  - `test_create_agent_with_valid_data_returns_201()`
  - `test_chat_with_no_api_key_returns_401()`
  - `test_agent_uses_tool_when_requested_returns_result()`

**Test Classes:**
- `Test<Feature>` for grouping related tests
- Example: `TestAgentCreation`, `TestChatEndpoint`

---

## 3. Shared Test Fixtures & Utilities

### Global Fixtures (conftest.py)

```python
# tests/conftest.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base

# ==================== DATABASE ====================

@pytest.fixture(scope="session")
def test_database_url():
    """Test database URL from environment"""
    return "sqlite:///test.db"

@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create test database engine"""
    engine = create_engine(test_database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Get fresh database session for each test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

# ==================== API CLIENT ====================

@pytest.fixture
def client(db_session):
    """FastAPI TestClient with mocked database"""
    def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

# ==================== AUTHENTICATION ====================

@pytest.fixture
def valid_api_key():
    """Valid API key for testing"""
    return "test-api-key-12345"

@pytest.fixture
def api_key_header(valid_api_key):
    """Headers with valid API key"""
    return {"X-API-Key": valid_api_key}

# ==================== LLM MOCKING ====================

@pytest.fixture
def mock_litellm(monkeypatch):
    """Mock LiteLLM completion calls"""
    def mock_completion(**kwargs):
        return {"choices": [{"message": {"content": "Mocked response"}}]}
    
    monkeypatch.setattr("litellm.completion", mock_completion)

# ==================== ASYNC SUPPORT ====================

@pytest.fixture
def event_loop():
    """Event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ==================== MARKERS ====================

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
```

### pytest Configuration (pytest.ini)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    -ra
    --tb=short
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
asyncio_mode = auto

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    slow: Slow tests
```

---

## 4. Test Cases Mapped to Functional Requirements

Each of the 90 FRs has been mapped to specific test cases. Key examples:

### Framework Core (FR1-FR10) → 30+ test cases
- Configuration loading, YAML parsing, environment overrides
- Hot reload, sensible defaults
- Multiple environments

### Agent Development (FR11-FR20) → 25+ test cases
- Template generation, customization
- Local testing, CLI playground
- Error feedback, type hints

### Tool System (FR21-FR30) → 35+ test cases
- Decorator registration, input validation
- Tool discovery, class-based extensions
- Tool hooks, error handling

### LLM Integration (FR31-FR40) → 40+ test cases
- Provider support (OpenAI, Anthropic, Azure)
- Provider switching, retry logic
- Token counting, cost tracking
- Mocking for tests

### Memory & Context (FR41-FR50) → 30+ test cases
- PostgreSQL persistence
- Memory strategies (full, rolling, summary)
- Session persistence
- Custom strategies

### Execution & Reasoning (FR51-FR60) → 28+ test cases
- Message processing, tool execution
- Planning mode (chain-of-thought)
- Guardrails, grounding
- Fallback behavior

### Observability (FR61-FR70) → 25+ test cases
- Structured logging, trace IDs
- Debug mode
- Metrics dashboard
- Log filtering, Prometheus export

### Security & Compliance (FR71-FR80) → 35+ test cases
- API key management
- Encryption at rest
- HTTPS/TLS
- PII detection/masking
- Audit logging
- Rate limiting (requests + cost)
- Content moderation
- GDPR compliance

### REST API (FR81-FR90) → 30+ test cases
- All endpoints (CRUD agents, sessions, chat)
- Health checks, metrics endpoint
- OpenAPI documentation
- Input validation
- Authentication/authorization

### Operations (FR91-FR100) → 20+ test cases
- Docker build
- Kubernetes Helm charts
- Health probes
- Scaling, stateless design
- Automatic migrations

**Total: 318+ test cases mapped to 90 FRs**

---

## 5. Performance Test Specifications

### Response Time Tests

```python
# tests/performance/test_response_time.py

@pytest.mark.performance
async def test_simple_agent_response_under_3_seconds(agent_fixture):
    """NFR-01: Simple queries < 3s"""
    response = await agent_fixture.chat("What's 2+2?")
    assert response.elapsed_time < 3.0

@pytest.mark.performance
async def test_complex_query_under_15_seconds(agent_fixture):
    """NFR-02: Complex queries with planning < 15s"""
    response = await agent_fixture.chat(
        "Create marketing plan",
        enable_planning=True
    )
    assert response.elapsed_time < 15.0

@pytest.mark.performance
async def test_api_latency_excluding_llm_under_500ms(client, mock_litellm):
    """NFR-03: API latency (excl. LLM) < 500ms"""
    response = client.post("/agents/1/chat", json={"message": "test"})
    assert response.response_time < 0.5
```

### Concurrency Tests

```python
# tests/performance/test_concurrent_calls.py

@pytest.mark.performance
async def test_handle_100_concurrent_requests(client):
    """NFR-05: Support 100+ concurrent calls"""
    tasks = [make_request_async() for _ in range(100)]
    results = await asyncio.gather(*tasks)
    assert all(r.status_code == 200 for r in results)
```

---

## 6. Test Coverage Goals by Component

| Component | Unit | Integration | E2E | Target |
|-----------|------|-------------|-----|--------|
| API Routes | 100% | 100% | 100% | **100%** |
| Database Models | 100% | 100% | - | **100%** |
| Agent Executor | 90% | 100% | 90% | **95%** |
| Tool System | 95% | 100% | 85% | **95%** |
| LLM Integration | 85% | 90% | 80% | **85%** |
| Memory Strategies | 90% | 100% | 90% | **95%** |
| Security/Auth | 100% | 100% | 95% | **100%** |
| Error Handling | 90% | 95% | 85% | **90%** |
| **Overall Target** | - | - | - | **≥80%** |

---

## 7. GitHub Actions CI/CD Configuration

```yaml
# .github/workflows/test.yml

name: Test Suite

on:
  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_PASSWORD: test

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      
      - name: Format check (Black)
        run: black --check app/ tests/
      
      - name: Lint (Flake8)
        run: flake8 app/ tests/
      
      - name: Type check (mypy)
        run: mypy app/
      
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=app
      
      - name: Run integration tests
        run: pytest tests/integration/ -v
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
      
      - name: Verify coverage ≥80%
        run: coverage report --fail-under=80
```

---

## 8. Local Testing Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_agents/test_executor.py -v

# Run performance tests
pytest tests/performance/ -v

# Watch mode (auto-rerun on file change)
pytest-watch

# Run with verbose output
pytest -v -s
```

---

## 9. Testing Checklist Before Implementation

### Pre-Implementation Phase

- [ ] Test strategy reviewed and approved
- [ ] Test data fixtures defined
- [ ] Mock strategy confirmed
- [ ] conftest.py configured
- [ ] pytest.ini configured
- [ ] CI/CD pipeline set up
- [ ] Local test environment working

### For Each Feature Implementation

- [ ] Write test cases FIRST (TDD)
- [ ] Tests verify PRD requirements
- [ ] Unit tests: happy path + error cases
- [ ] Integration tests: component interactions
- [ ] Performance tests: for critical paths
- [ ] Code coverage reported (≥80%)

### Before Merge to Main

- [ ] All tests passing (unit + integration + e2e)
- [ ] Coverage ≥80%
- [ ] Linting passes (Black, Flake8, mypy)
- [ ] Performance benchmarks met
- [ ] Documentation updated

### Before Production Deployment

- [ ] All E2E tests passing
- [ ] Load tests passed
- [ ] Security tests passed
- [ ] Staging deployment verified

---

## 10. Next Steps

1. **Validate** this test strategy with team
2. **Create** conftest.py with shared fixtures
3. **Create** test data factories
4. **Configure** GitHub Actions CI/CD
5. **Write** test cases for each feature
6. **Implement** code to pass tests (TDD)
7. **Monitor** coverage with each PR
8. **Iterate** on test strategy as needed

---

**This test-first approach ensures:**
- ✅ Clear requirements (tests define contracts)
- ✅ Comprehensive coverage (all paths tested)
- ✅ Regression prevention (breaking changes caught)
- ✅ Confidence in refactoring (tests prove correctness)
- ✅ Living documentation (tests show usage)

**Total Test Cases Planned: 318+**  
**Target Coverage: ≥80%**  
**Critical Path Coverage: 100%**
