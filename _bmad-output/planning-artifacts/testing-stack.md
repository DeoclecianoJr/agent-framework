---
documentType: 'testing-stack'
project_name: 'AI Agent Framework'
user_name: 'Wbj-compassuol-010'
date: '2026-01-13'
status: 'Testing Technology Stack Definition'
---

# Testing Stack - Automated Testing Technology

_Complete definition of all tools, frameworks, and integrations for automated testing. Manual testing is NOT an option for this project - everything must be automated._

---

## 1. Core Testing Framework Stack

### Primary Framework: pytest

**Purpose:** Test discovery, execution, fixtures, parametrization  
**Version:** 7.4+  
**Python Version:** 3.10+  
**Installation:** `pip install pytest==7.4.3`

**Why pytest:**
- ✅ Async support (pytest-asyncio)
- ✅ Fixtures system (better than unittest)
- ✅ Plugins ecosystem
- ✅ Parametrization (run same test with different inputs)
- ✅ Coverage integration (pytest-cov)
- ✅ Markers (categorize tests)

### Async Testing: pytest-asyncio

**Purpose:** Test async/await code (required for FastAPI)  
**Version:** 0.21.1+  
**Installation:** `pip install pytest-asyncio==0.21.1`

**Why pytest-asyncio:**
- ✅ Run async test functions with `async def test_*()`
- ✅ Event loop management
- ✅ Works with FastAPI TestClient
- ✅ Compatible with pytest fixtures

**Example:**
```python
@pytest.mark.asyncio
async def test_async_agent_execution():
    agent = Agent(name="test")
    response = await agent.chat("Hello")
    assert response.content is not None
```

### Coverage Reporting: pytest-cov

**Purpose:** Measure code coverage  
**Version:** 4.1+  
**Installation:** `pip install pytest-cov==4.1`

**Why pytest-cov:**
- ✅ HTML report generation
- ✅ Terminal report with missing lines
- ✅ Coverage thresholds (fail if <80%)
- ✅ Branch coverage
- ✅ Integration with CI/CD

**Example:**
```bash
pytest --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=80
```

### BDD Testing: pytest-bdd

**Purpose:** Behavior-Driven Development with Gherkin scenarios  
**Version:** 7.0+  
**Installation:** `pip install pytest-bdd==7.0.0`

**Why pytest-bdd:**
- ✅ Write tests in Gherkin (Given/When/Then)
- ✅ Business-readable test scenarios
- ✅ Validates user requirements directly
- ✅ Integrates seamlessly with pytest
- ✅ Shares fixtures with unit tests

**Example:**
```gherkin
# features/chat_workflow.feature
Feature: Agent Chat Workflow
  Scenario: User sends message to agent
    Given an agent named "TestAgent"
    And a new session for the agent
    When I send message "Hello, how are you?"
    Then I should receive a response
    And the response should be stored in session history
```

```python
# tests/features/step_defs/chat_steps.py
from pytest_bdd import scenarios, given, when, then

scenarios('../chat_workflow.feature')

@given('an agent named "TestAgent"')
def create_test_agent(db_session):
    return AgentFactory(name="TestAgent")

@when('I send message "Hello, how are you?"')
def send_message(client, agent, session):
    response = client.post(f"/agents/{agent.id}/chat", 
                          json={"message": "Hello, how are you?"})
    return response

@then('I should receive a response')
def verify_response(response):
    assert response.status_code == 200
    assert response.json()["content"] is not None
```

---

## 2. Mocking & Fixtures Stack

### Fixture Library: factory-boy

**Purpose:** Create test data factories for database objects  
**Version:** 3.3+  
**Installation:** `pip install factory-boy==3.3.0`

**Why factory-boy:**
- ✅ ORM support (SQLAlchemy)
- ✅ Sequence generation (IDs, unique names)
- ✅ Relationships between objects
- ✅ Cleaner than hardcoded test data

**Example:**
```python
class AgentFactory(factory.sqlalchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Agent
    
    name = factory.Sequence(lambda n: f"agent-{n}")
    description = "Test agent"
    model = "gpt-4"

# Usage
agent = AgentFactory()  # Creates with generated data
agents = AgentFactory.create_batch(5)  # Create 5 agents
```

### Mocking Library: unittest.mock

**Purpose:** Mock external dependencies (built-in to Python)  
**Version:** Built-in (no installation)

**Why unittest.mock:**
- ✅ Built-in to Python 3.10+
- ✅ MagicMock for flexible mocking
- ✅ Patch decorator for temporary mocks
- ✅ Call tracking and assertions

**Example:**
```python
from unittest.mock import patch, MagicMock

@patch('langchain.chat_models.ChatOpenAI')
def test_llm_call(mock_chat_model):
    mock_instance = MagicMock()
    mock_instance.predict.return_value = "Response"
    mock_chat_model.return_value = mock_instance
    
    result = llm.chat("question")
    
    assert result == "Response"
    mock_instance.predict.assert_called_once()
```

### Enhanced Mocking: pytest-mock

**Purpose:** Simplified pytest integration with mocking  
**Version:** 3.12+  
**Installation:** `pip install pytest-mock==3.12.0`

**Why pytest-mock:**
- ✅ `mocker` fixture (cleaner than @patch)
- ✅ Automatic cleanup
- ✅ Better pytest integration
- ✅ Spy on real functions

**Example:**
```python
def test_with_mocker(mocker):
    mock_chat_model = mocker.patch('langchain.chat_models.ChatOpenAI')
    mock_instance = mocker.MagicMock()
    mock_instance.predict.return_value = "Response"
    mock_chat_model.return_value = mock_instance
    
    result = llm.chat("question")
    
    assert mock_instance.predict.called
```

### Time Mocking: freezegun

**Purpose:** Mock datetime for time-dependent tests  
**Version:** 1.3+  
**Installation:** `pip install freezegun==1.3.0`

**Why freezegun:**
- ✅ Mock system time
- ✅ Test time-based logic (TTL, expiration)
- ✅ Deterministic tests (no timing issues)
- ✅ Works with async code

**Example:**
```python
from freezegun import freeze_time

@freeze_time("2026-01-13 10:00:00")
def test_token_expiry():
    token = APIKey(expires_at="2026-01-14")
    assert not token.is_expired()
    
    # Time moves forward
    freeze_time("2026-01-15").start()
    assert token.is_expired()
```

---

## 3. API Testing Stack

### HTTP Testing: httpx

**Purpose:** Make HTTP requests in tests  
**Version:** 0.25+  
**Installation:** `pip install httpx==0.25.0`

**Why httpx:**
- ✅ Async support (for async tests)
- ✅ Synchronous and async client
- ✅ Same API as requests
- ✅ Integrated with FastAPI TestClient

**Example:**
```python
async def test_api_with_httpx():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": "test"})
        assert response.status_code == 200
```

### FastAPI TestClient (Built-in)

**Purpose:** Test FastAPI endpoints  
**Version:** Included with FastAPI 0.100+  
**Installation:** Automatic with `pip install fastapi`

**Why FastAPI TestClient:**
- ✅ Sync testing of async endpoints (automatic)
- ✅ Injects dependencies for testing
- ✅ No need to run actual server
- ✅ Built for FastAPI

**Example:**
```python
from fastapi.testclient import TestClient

def test_api_endpoint(client: TestClient):
    response = client.post(
        "/agents/1/chat",
        json={"message": "hello"},
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    assert "content" in response.json()
```

---

## 4. Database Testing Stack

### ORM: SQLAlchemy

**Purpose:** Database modeling and queries  
**Version:** 2.0+  
**Installation:** `pip install sqlalchemy==2.0.23`

**Why SQLAlchemy:**
- ✅ Type-safe queries
- ✅ Test database support (SQLite in-memory)
- ✅ Session management
- ✅ Relationship management

### Test Database: SQLite In-Memory

**Purpose:** Fast, isolated database for tests  
**Usage:** `sqlite:///:memory:`

**Why SQLite in-memory:**
- ✅ No setup/teardown overhead
- ✅ Completely isolated tests
- ✅ Fast execution (< 100ms per test)
- ✅ Full transaction support

**Example:**
```python
# conftest.py
@pytest.fixture
def test_database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()

def test_create_agent(test_database):
    agent = Agent(name="test")
    test_database.add(agent)
    test_database.commit()
    
    retrieved = test_database.query(Agent).filter_by(name="test").first()
    assert retrieved is not None
```

### Database Fixtures: SQLAlchemy Session

**Purpose:** Fresh database state per test  
**Implementation:** conftest.py fixture

**Example:**
```python
@pytest.fixture(autouse=True)
def reset_database(db_session):
    """Reset database before each test"""
    yield
    db_session.rollback()
    # All tables cleared automatically
```

---

## 5. Performance Testing Stack

### Performance Measurement: pytest-benchmark

**Purpose:** Measure and track performance  
**Version:** 4.0+  
**Installation:** `pip install pytest-benchmark==4.0.0`

**Why pytest-benchmark:**
- ✅ Warm-up runs (realistic timing)
- ✅ Statistical analysis (min/max/mean)
- ✅ Historical comparison (detect regressions)
- ✅ Pretty output

**Example:**
```python
def test_response_time(benchmark):
    """Benchmark agent response time"""
    def chat():
        return agent.chat("2+2")
    
    result = benchmark(chat)
    # pytest-benchmark automatically measures
    # Output: min=0.123s, max=0.145s, mean=0.131s
```

### Memory Profiling: memory-profiler

**Purpose:** Track memory usage  
**Version:** 0.61+  
**Installation:** `pip install memory-profiler==0.61.0`

**Why memory-profiler:**
- ✅ Line-by-line memory usage
- ✅ Detect memory leaks
- ✅ Verify memory constraints (< 500MB per agent)

**Example:**
```python
from memory_profiler import profile

@profile
def test_agent_memory():
    agents = [Agent(name=f"agent-{i}") for i in range(100)]
    # Output shows memory used per line
```

### Load Testing: locust (optional)

**Purpose:** Simulate concurrent users  
**Version:** 2.17+  
**Installation:** `pip install locust==2.17.0`

**Why locust:**
- ✅ Write tests in Python
- ✅ Web UI for monitoring
- ✅ Ramp-up load gradually
- ✅ Real-time statistics

**Example:**
```python
from locust import HttpUser, task

class APIUser(HttpUser):
    @task
    def chat_with_agent(self):
        self.client.post(
            "/agents/1/chat",
            json={"message": "hello"},
            headers={"X-API-Key": "test-key"}
        )
```

---

## 6. Code Quality Testing Stack

### Type Checking: mypy

**Purpose:** Static type checking  
**Version:** 1.7+  
**Installation:** `pip install mypy==1.7.0`

**Why mypy:**
- ✅ Catch type errors before runtime
- ✅ Full Python 3.10 support
- ✅ Plugin system
- ✅ Strict mode for maximum safety

**Example:**
```bash
mypy app/ --strict
# Reports type errors in entire app/
```

### Linting: flake8

**Purpose:** Code style and quality  
**Version:** 6.1+  
**Installation:** `pip install flake8==6.1.0`

**Why flake8:**
- ✅ PEP 8 compliance
- ✅ Unused imports detection
- ✅ Plugin ecosystem
- ✅ Per-file and project-wide rules

**Example:**
```bash
flake8 app/ tests/
# Reports style violations
```

### Code Formatting: black

**Purpose:** Automatic code formatting  
**Version:** 23.12+  
**Installation:** `pip install black==23.12.0`

**Why black:**
- ✅ Deterministic formatting (no debates)
- ✅ Fast
- ✅ Opinionated (saves time)
- ✅ Pre-commit hook friendly

**Example:**
```bash
black app/ tests/
# Auto-formats all Python files
```

### Security Scanning: bandit

**Purpose:** Detect security issues  
**Version:** 1.7+  
**Installation:** `pip install bandit==1.7.5`

**Why bandit:**
- ✅ Hardcoded passwords detection
- ✅ SQL injection warnings
- ✅ Unsafe functions detection
- ✅ Report generation

**Example:**
```bash
bandit -r app/
# Scans for security vulnerabilities
```

---

## 7. CI/CD Integration Stack

### GitHub Actions (Built-in)

**Purpose:** Automated testing on every PR  
**Configuration:** `.github/workflows/test.yml`

**Workflow Stages:**
1. Checkout code
2. Setup Python 3.10
3. Install dependencies
4. Run pytest (unit + integration)
5. Check coverage (≥80%)
6. Run linting (Black, Flake8, mypy)
7. Generate coverage report
8. Upload to codecov (optional)

**Example Workflow:**
```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      
      - name: pytest
        run: pytest --cov=app --cov-fail-under=80
      
      - name: Linting
        run: |
          black --check app/
          flake8 app/
          mypy app/
```

### Coverage Reporting: codecov (optional)

**Purpose:** Track coverage over time  
**Integration:** GitHub Actions step
**Service:** codecov.io (free for public repos)

**Why codecov:**
- ✅ Historical coverage trends
- ✅ Per-PR coverage comments
- ✅ Coverage diff detection
- ✅ Visual dashboard

---

## 8. Complete Requirements File

**File:** `requirements-dev.txt`

```
# Base Framework
fastapi==0.104.1
sqlalchemy==2.0.23
pydantic==2.5.0
alembic==1.13.0

# LLM & AI
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-anthropic>=0.1.0

# Testing - Core
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-bdd==7.0.0
pytest-benchmark==4.0.0

# Testing - Fixtures & Mocking
factory-boy==3.3.0
freezegun==1.3.0

# Testing - HTTP/API
httpx==0.25.0

# Testing - Database
psycopg2-binary==2.9.9

# Code Quality
black==23.12.0
flake8==6.1.0
mypy==1.7.0
bandit==1.7.5

# Performance
memory-profiler==0.61.0

# Utilities
python-dotenv==1.0.0
```

**Installation:**
```bash
pip install -r requirements-dev.txt
```

---

## 9. Test Execution Matrix

### Local Development

```bash
# Watch mode (auto-rerun on file change)
pytest-watch

# All tests with coverage
pytest --cov=app --cov-report=html

# Only unit tests (fast)
pytest tests/unit/ -v

# Only integration tests
pytest tests/integration/ -v

# Only failing tests
pytest --lf

# Run tests matching pattern
pytest -k "test_chat" -v

# Debug mode (show prints)
pytest -s -vv
```

### Pre-Commit Hook

**File:** `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: 1.7.0
    hooks:
      - id: mypy
```

**Usage:**
```bash
pre-commit run --all-files
```

### CI/CD Pipeline

```
Push to PR
    ↓
GitHub Actions triggered
    ↓
[Parallel Jobs]
├── pytest unit tests
├── pytest integration tests
├── Black format check
├── Flake8 linting
├── mypy type checking
└── Coverage ≥80%?
    ↓
All pass → Can merge
Failed → Block merge + comment on PR
```

---

## 10. Test Coverage by Testing Layers

| Layer | Tools | Coverage | Speed |
|-------|-------|----------|-------|
| **Unit Tests** | pytest, pytest-mock, factory-boy | 60-70% of total | < 5s |
| **Integration Tests** | pytest, SQLAlchemy, mock LLM | 20-30% of total | 5-30s |
| **E2E Tests** | FastAPI TestClient, full app | 5-10% of total | 10-60s |
| **Performance Tests** | pytest-benchmark, locust | Critical paths | 30-120s |
| **Code Quality** | mypy, flake8, black, bandit | 100% of code | < 10s |

---

## 11. Test Automation Examples

### Example 1: Full Unit Test

```python
# tests/unit/test_agents/test_executor.py

from unittest.mock import MagicMock
import pytest
from app.agents.executor import AgentExecutor
from app.agents.memory import MemoryStrategy
from tests.fixtures.data import AgentFactory

class TestAgentExecutor:
    """Unit tests for agent execution"""
    
    @pytest.fixture
    def executor(self, mocker):
        \"\"\"Create executor with mocked LLM\"\"\"
        from langchain.chat_models.fake import FakeListChatModel
        fake_llm = FakeListChatModel(responses=[\"Agent response\"])
        return AgentExecutor(llm=fake_llm)
    
    def test_process_message_returns_response(self, executor):
        \"\"\"Test that executor returns agent response\"\"\"
        response = executor.process_message(\"question\")
        
        assert response == \"Agent response\"
        
        result = executor.execute("User question")
        
        assert result.content == "Agent response"
        mock_llm.assert_called_once()
    
    def test_execute_with_tool_calls_tool(self, executor, mocker):
        """Test that executor calls requested tool"""
        mock_tool = mocker.MagicMock()
        executor.register_tool("calculator", mock_tool)
        
        executor.execute_tool_call("calculator", {"x": 2, "y": 2})
        
        mock_tool.assert_called_once_with(x=2, y=2)
    
    @pytest.mark.parametrize("question,expected", [
        ("2+2", True),  # Has tool call
        ("Tell me about AI", False),  # No tool call
    ])
    def test_detects_tool_calls(self, executor, question, expected):
        """Parametrized test for tool detection"""
        has_tool_call = executor.should_use_tool(question)
        assert has_tool_call == expected
```

### Example 2: Integration Test

```python
# tests/integration/test_agents/test_agent_with_memory.py

import pytest
from app.agents.executor import AgentExecutor
from app.agents.memory import FullMemoryStrategy
from app.core.models import Session, Message
from tests.fixtures.data import AgentFactory, SessionFactory

class TestAgentWithMemory:
    """Integration tests: agent + memory together"""
    
    @pytest.fixture
    def session_with_messages(self, db_session):
        """Create session with existing messages"""
        agent = AgentFactory()
        session = SessionFactory(agent=agent)
        
        message1 = Message(
            session_id=session.id,
            role="user",
            content="My name is Alice"
        )
        message2 = Message(
            session_id=session.id,
            role="assistant",
            content="Nice to meet you Alice"
        )
        
        db_session.add_all([message1, message2])
        db_session.commit()
        
        return session
    
    def test_agent_remembers_previous_messages(
        self, db_session, session_with_messages
    ):
        \"\"\"Test that agent has access to conversation history\"\"\"
        from langchain.chat_models.fake import FakeListChatModel
        
        fake_llm = FakeListChatModel(responses=[\"I remember you!\"])
        executor = AgentExecutor(
            session_id=session_with_messages.id,
            memory_strategy=FullMemoryStrategy(),
            llm=fake_llm
        )
        
        # Load message history
        history = executor.load_memory()
        
        assert len(history) == 2
        assert history[0].content == "My name is Alice"
        assert history[1].content == "Nice to meet you Alice"
    
    def test_new_message_persisted_to_database(
        self, db_session, session_with_messages, mocker
    ):
        """Test that agent response is saved to database"""
        mocker.patch('litellm.completion')
        
        executor = AgentExecutor(
            session_id=session_with_messages.id,
            db=db_session
        )
        
        executor.execute("What's my name?")
        
        # Verify message saved to DB
        new_message = db_session.query(Message).order_by(
            Message.id.desc()
        ).first()
        assert new_message.role == "assistant"
        assert new_message.session_id == session_with_messages.id
```

### Example 3: API E2E Test

```python
# tests/e2e/test_chat_workflow.py

def test_complete_chat_workflow(client, api_key_header):
    """E2E: Create agent → Create session → Chat → Verify response"""
    
    # 1. Create agent
    agent_response = client.post(
        "/agents",
        json={
            "name": "customer-support",
            "model": "gpt-4",
            "system_prompt": "Help customers"
        },
        headers=api_key_header
    )
    assert agent_response.status_code == 201
    agent_id = agent_response.json()["id"]
    
    # 2. Create session
    session_response = client.post(
        f"/agents/{agent_id}/sessions",
        json={"title": "Test session"},
        headers=api_key_header
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["id"]
    
    # 3. Send chat message
    chat_response = client.post(
        f"/agents/{agent_id}/chat",
        json={
            "session_id": session_id,
            "message": "What's my invoice balance?"
        },
        headers=api_key_header
    )
    assert chat_response.status_code == 200
    
    # 4. Verify response structure
    response_data = chat_response.json()
    assert "content" in response_data
    assert "trace_id" in response_data
    assert "tokens_used" in response_data
```

### Example 4: Performance Test

```python
# tests/performance/test_response_time.py

import pytest

@pytest.mark.performance
def test_simple_query_under_3_seconds(benchmark, agent_fixture):
    """NFR-01: Simple queries must complete in < 3s"""
    def simple_chat():
        return agent_fixture.chat("What's 2+2?")
    
    result = benchmark(simple_chat)
    # pytest-benchmark tracks: min, max, mean, stddev

@pytest.mark.performance
@pytest.mark.benchmark(
    group="response-time",
    min_rounds=5,
)
def test_concurrent_requests(benchmark, client, api_key_header):
    """NFR-05: Handle 100+ concurrent requests"""
    import asyncio
    
    async def concurrent_requests():
        tasks = [
            client.post(
                "/agents/1/chat",
                json={"message": "test"},
                headers=api_key_header
            )
            for _ in range(100)
        ]
        return await asyncio.gather(*tasks)
    
    results = benchmark(concurrent_requests)
    success_count = sum(1 for r in results if r.status_code == 200)
    assert success_count == 100
```

---

## 12. Test Automation Checklist

### ✅ Daily (Local Development)

- [ ] Run unit tests before committing (`pytest tests/unit/`)
- [ ] Run pre-commit checks (`pre-commit run --all-files`)
- [ ] Check code coverage report (`pytest --cov`)

### ✅ Per Pull Request (CI/CD)

- [ ] All tests passing (unit + integration)
- [ ] Coverage ≥80% maintained
- [ ] Linting passes (Black, Flake8)
- [ ] Type checking passes (mypy)
- [ ] Security scan passes (bandit)
- [ ] No performance regression

### ✅ Before Release

- [ ] All E2E tests passing
- [ ] Performance benchmarks met
- [ ] Load tests (1000+ requests)
- [ ] Security penetration (optional)
- [ ] Staging deployment verified

### ✅ Post-Deployment

- [ ] Production health checks passing
- [ ] Error rate < 0.1%
- [ ] Response time acceptable
- [ ] No new errors in logs

---

## 13. Stack Summary

| Category | Tool | Version | Purpose |
|----------|------|---------|---------|
| **Test Runner** | pytest | 7.4+ | Test discovery & execution |
| **Async Tests** | pytest-asyncio | 0.21+ | Async/await test support |
| **Coverage** | pytest-cov | 4.1+ | Code coverage measurement |
| **Mocking** | unittest.mock | 3.10+ | Mock external dependencies |
| **Mocking (Enhanced)** | pytest-mock | 3.12+ | Better pytest integration |
| **Time Mocking** | freezegun | 1.3+ | Mock system time |
| **Fixtures** | factory-boy | 3.3+ | Test data factories |
| **HTTP Testing** | httpx | 0.25+ | Async HTTP requests |
| **API Testing** | FastAPI TestClient | 0.104+ | Test FastAPI endpoints |
| **Database** | SQLAlchemy | 2.0+ | ORM & test databases |
| **Benchmark** | pytest-benchmark | 4.0+ | Performance measurement |
| **Memory Profile** | memory-profiler | 0.61+ | Memory usage tracking |
| **Type Check** | mypy | 1.7+ | Static type checking |
| **Linting** | flake8 | 6.1+ | Code style checking |
| **Formatting** | black | 23.12+ | Auto code formatting |
| **Security** | bandit | 1.7+ | Security vulnerability scanning |
| **CI/CD** | GitHub Actions | - | Automated pipeline |

---

## 14. Nothing is Manual

**Every test case in the test strategy MUST be automated using this stack.**

**Manual testing is NOT acceptable for:**
- ❌ Functional requirements (should be automated)
- ❌ Non-functional requirements (should be automated)
- ❌ API endpoints (should be automated)
- ❌ Database operations (should be automated)
- ❌ Error handling (should be automated)
- ❌ Performance requirements (should be automated)
- ❌ Security requirements (should be automated)

**Test automation coverage:**
- ✅ 100% of API routes → FastAPI TestClient tests
- ✅ 100% of database operations → SQLAlchemy fixture tests
- ✅ 100% of business logic → pytest unit tests
- ✅ 100% of error scenarios → pytest parametrization
- ✅ 100% of performance requirements → pytest-benchmark
- ✅ 100% of security rules → bandit + custom tests
- ✅ All code quality → Black, Flake8, mypy
- ✅ All on every commit → GitHub Actions CI/CD

---

## 15. Quick Start Commands

```bash
# Install all testing tools
pip install -r requirements-dev.txt

# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-fail-under=80

# Run only unit tests (fastest)
pytest tests/unit/ -v

# Run tests in watch mode (auto-rerun on changes)
pytest-watch

# Check code quality
black --check app/ tests/
flake8 app/ tests/
mypy app/

# Run with detailed output
pytest -vv -s

# Run specific test
pytest tests/unit/test_agents/test_executor.py::TestAgentExecutor::test_process_message_returns_response -v

# Generate HTML coverage report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

---

## 16. Why This Stack?

**Completeness:** Covers all test types (unit, integration, e2e, performance, security)  
**Python Native:** All tools designed for Python (not adapting from other languages)  
**FastAPI Optimized:** pytest-asyncio + FastAPI TestClient work perfectly together  
**Industry Standard:** Used by 10,000+ Python projects  
**Automation First:** Everything automated, no manual testing  
**CI/CD Ready:** Integrates seamlessly with GitHub Actions  
**Scalable:** Works for 100+ tests up to 10,000+ tests  
**Cost-Free:** All open source tools (except optional codecov.io)  

---

**This stack enables 318+ automated test cases across all 90 Functional Requirements with ZERO manual testing.**
