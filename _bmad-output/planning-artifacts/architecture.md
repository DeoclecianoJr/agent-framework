---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'tech-stack-update']
inputDocuments: ['planning-artifacts/prd.md']
workflowType: 'architecture'
project_name: 'AI Agent Framework'
user_name: 'Wbj-compassuol-010'
date: '2026-01-13'
lastUpdated: '2026-01-16'
technicalDecisions:
  llmAbstraction: 'LangChain'
  database: 'PostgreSQL (no Redis)'
  testingApproach: 'TDD + BDD'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Architectural decisions are documented as we work through each domain together._

---

## Project Context Analysis

### Requirements Overview

**Project Type:** Framework/SDK (Platform thinking)  
**Domain:** AI/Machine Learning + Enterprise Software  
**Complexity:** Medium-High (greenfield)  
**Language:** Python ≥3.10  
**Cloud:** GCP (development), flexible for production  

### Functional Architecture

**90 Functional Requirements** organized into 10 capability areas define what the framework must do:

1. **Framework Core** (FR1-FR10): Installation, YAML configuration, environment overrides, multiple environments, programmatic config, hot reload, sensible defaults
2. **Agent Development** (FR11-FR20): Templates, customization, local testing, CLI playground, error feedback, type hints
3. **Tool/Plugin System** (FR21-FR30): Decorator registration, validation, discovery, class-based extension, hooks
4. **LLM Integration** (FR31-FR40): OpenAI, Anthropic, Azure support, provider switching, abstraction, retry, fallback, mocking, token tracking
5. **Memory & Context** (FR41-FR50): PostgreSQL persistence, full/rolling/summary strategies, auto-management, session persistence, custom strategies
6. **Execution & Reasoning** (FR51-FR60): Message processing, tool execution, planning (chain-of-thought), guardrails, grounding, fallback
7. **Observability** (FR61-FR70): Structured logging, trace IDs, debug mode, metrics dashboard, filtering, Prometheus export
8. **Security & Compliance** (FR71-FR80): API key management, encryption, HTTPS/TLS, PII detection/masking, audit logs, rate limiting, content moderation
9. **REST API** (FR81-FR90): POST /chat, GET /session, DELETE /session, health checks, metrics, OpenAPI, validation
10. **Operations** (FR91-FR100): Dockerfile, Helm charts, health probes, horizontal scaling, stateless design, automatic migrations

### Quality Requirements (Non-Functional)

**37 Non-Functional Requirements** define quality attributes:

**Performance (7 NFRs):**
- Agent response < 3s (simple), < 15s (with planning)
- API latency < 500ms (excluding LLM)
- Dashboard load < 2s
- Support 100+ concurrent calls
- < 500MB memory per agent

**Security & Compliance (9 NFRs):**
- AES-256 encryption at rest
- TLS 1.2+ for all communications
- LGPD deletion < 24 hours
- Audit retention ≥ 90 days
- > 90% PII detection accuracy
- > 95% content moderation recall
- API key rotation without downtime

**Scalability (7 NFRs):**
- Horizontal scaling without reconfiguration
- MVP: 10-20 simultaneous agents
- 12-month: 100+ simultaneous agents
- < 10% latency at 10x load
- Stateless design
- Efficient connection pooling

**Integration & Reliability (7 NFRs):**
- Automatic LLM provider fallback
- 3 retries with exponential backoff
- ACID transactions
- Circuit breakers for external APIs
- 99% uptime target
- Recovery without data loss

**Maintainability (7 NFRs):**
- ≥80% test coverage
- 100% public API type hints
- Docstrings for all modules
- CI/CD < 5 minutes
- Versioned automatic migrations
- Breaking changes in major versions only

### Core Architectural Components

**9 Major Components** identified from requirements analysis:

1. **SDK Core (Python Package)**
   - Agent decorators: `@ai_framework.agent` for agent definition
   - Tool decorators: `@ai_framework.tool` for tool registration
   - Tool execution engine with parameter validation
   - Configuration management (YAML per-agent)
   - CLI playground for interactive testing

2. **LLM Abstraction Layer** (LiteLLM)
   - Provider abstraction: OpenAI, Anthropic, Azure OpenAI
   - Token counting, cost tracking
   - Retry logic, automatic fallback
   - Rate limiting, provider registry
   - Mock provider for testing

3. **Memory & Context Management** (PostgreSQL)
   - Session persistence and conversation history
   - Multiple strategies: full, rolling window, automatic summarization
   - Context window auto-management
   - PostgreSQL-only design (no additional cache layer for MVP)

4. **Runtime API** (FastAPI)
   - Chat interaction endpoints: POST /chat, GET /chat/{session_id}/messages
   - Session management: no agent CRUD (agents defined in code via SDK)
   - Message persistence and history
   - API key authentication via middleware
   - OpenAPI/Swagger documentation

5. **Configuration System**
   - YAML declarative configuration (per-agent)
   - Environment variable overrides
   - Per-environment configs (dev/staging/prod)
   - Hot reload in development mode
   - Pydantic schema validation

6. **Observability & Logging** (Structured)
   - JSON-formatted structured logging
   - Distributed trace IDs for request correlation
   - Debug mode with prompt visibility
   - Performance profiling per component

7. **Security & Compliance Layer**
   - PII detection and automatic masking
   - Encryption at rest (AES-256) and in transit (TLS 1.2+)
   - LGPD APIs for data deletion and export
   - Immutable audit logging
   - Content moderation and configurable guardrails
   - API key authentication

8. **Deployment Infrastructure**
   - Production-ready Dockerfile
   - Kubernetes/Helm charts for GKE
   - Alembic for database migrations
   - Health and readiness probes
   - Horizontal scaling support

### SDK vs Runtime API

**Critical Architectural Distinction:**

The framework consists of two layers with distinct responsibilities:

**SDK (Python Package - `ai_framework/`):**
- Used by developers to *define* agents in their code
- Provides decorators (`@agent`, `@tool`), abstractions, and utilities
- Installed via `pip install ai_framework`
- No REST API interaction - purely Python library

**Runtime API (FastAPI - `app/`):**
- Deployed as a service to *run* and *interact with* agents
- Provides REST endpoints for chat interaction
- Stateless, horizontally scalable
- For end-user chat interaction, not agent management
- NO agent CRUD endpoints (agents defined in code, deployed as part of application)

**Critical Design Point:**
- Agents are **created in code using the SDK**, not via API endpoints
- The API is **for interaction only** (sending messages, retrieving history)
- Agent configuration is **code-based or YAML-file-based**, not API-managed

### Critical Architectural Decisions Ahead

**Stateless Design Requirement:**
- All persistent state must be in PostgreSQL
- Application instances are stateless
- Enables horizontal scaling without session affinity
- Implications: shared database, cache invalidation strategy

**Provider Abstraction Strategy:**
- LangChain handles provider differences via `BaseChatModel` interface
- Fallback chain when primary provider fails via `langchain.llms.FallbackLLM`
- Token counting and cost tracking per provider via callback system
- Decision needed: retry policies, fallback order, degradation modes

**Context Window Management:**
- Multiple strategies (full, rolling, summarization)
- Auto-truncation vs summarization trade-offs
- Affects latency, memory usage, quality
- Decision needed: default strategy, per-agent overrides

**Tool Execution Architecture:**
- Agent decides when and what tools to call
- Tool result feeding back into context
- Parallel vs sequential execution
- Decision needed: tool result format, error handling

**Error Handling & Resilience:**
- Retry policies with exponential backoff
- Circuit breakers for failing services
- Graceful degradation patterns
- Decision needed: retry budgets, timeout thresholds, fallback behaviors

**Session & State Persistence:**
- PostgreSQL schema design for agents, sessions, messages
- Session lifecycle and cleanup
- Memory performance optimization
- Decision needed: schema design, indexing strategy, partitioning

**API Authentication & Rate Limiting:**
- API key authentication for access control
- Rate limiting to prevent abuse
- User-based vs API-key-based limits
- Decision needed: auth schema, rate limit strategy, cost-aware limits

**Observability Integration:**
- Structured logging for all operations
- Trace ID propagation across calls
- Metrics for latency, throughput, errors
- Decision needed: log levels, retention, sampling strategy

### Cross-Cutting Concerns

These architectural concerns affect multiple components and require systematic decisions:

1. **Error Handling & Retry Strategy** (affects LLM, tools, APIs)
2. **Logging & Tracing** (all components)
3. **Configuration & Environment** (all components)
4. **Context Window Management** (memory, reasoning)
5. **Provider Abstraction & Fallback** (LLM, cost tracking)
6. **Session & State Management** (memory, API)
7. **Database Performance** (PostgreSQL optimization)
8. **Security & Compliance** (all components)

### Scale Assessment

**MVP Target:**
- 10-20 simultaneous agents
- Single PostgreSQL instance
- Estimated 2-3 core architectural patterns needed
- 1-2 senior developers recommended

**12-Month Target:**
- 100+ simultaneous agents
- PostgreSQL replication
- Multi-cloud capability
- Extended feature set (Phase 2)

**Architectural Implications:**
- Must design for horizontal scaling from day 1
- Connection pooling critical at scale
- Caching strategy important for performance
- Event-driven architecture where beneficial

---

## Starter Template Evaluation

### Primary Technology Domain

**Identified Domain:** API Backend/Framework (Platform thinking)

Based on the PRD analysis:
- Project Type: Framework/SDK for AI agent development
- Primary Role: Backend service providing REST API for agent interactions
- Development Model: Library/framework as foundation for user applications
- Architecture Pattern: Stateless microservice-ready design

### Starter Options Considered

**Evaluated Options:**

1. **Cookiecutter FastAPI** (✅ Selected)
   - Full-stack template with PostgreSQL, SQLAlchemy, async/await
   - Pre-configured Alembic migrations, Pydantic v2 validation
   - Docker and Kubernetes ready
   - Feature-based project structure
   - Pre-commit hooks and testing setup

2. **FastAPI Project Generator**
   - Lighter weight alternative
   - Less scaffolding by default
   - Requires more manual setup

3. **Full Stack FastAPI PostgreSQL**
   - Includes frontend (React)
   - Overkill for backend framework
   - Adds unnecessary complexity

4. **Custom Minimal Setup**
   - Maximum flexibility
   - Requires establishing all patterns from scratch
   - Higher risk of inconsistency

### Selected Starter: Cookiecutter FastAPI

**Rationale for Selection:**

The Cookiecutter FastAPI starter aligns perfectly with the PRD requirements:

- **Technology Stack Match:** Python 3.10+, FastAPI, PostgreSQL, SQLAlchemy ORM, Alembic (exactly matches 90 FRs)
- **Async-First Design:** Built with async/await from the ground up (FR51-FR60 execution requirements)
- **Stateless Architecture:** Encourages separation of concerns between application and state (FR91-FR100 operations)
- **Production Ready:** Includes Docker, Kubernetes manifests, health checks (deployment ready)
- **Developer Experience:** Pre-configured testing, linting, formatting, debugging (FR11-FR20 agent dev)
- **Established Patterns:** Feature-based directory structure, clear separation of concerns
- **Maintenance Status:** Well-maintained, active community, regular updates

**Initialization Command:**

```bash
pip install cookiecutter
cookiecutter https://github.com/tiangolo/full-stack-fastapi-postgresql --checkout tags/0.12.0
```

Or via simplified command:
```bash
cookiecutter https://github.com/tiangolo/full-stack-fastapi-postgresql
```

When prompted, provide:
- **project_name:** `ai_agent_framework`
- **project_slug:** `ai_agent_framework`
- **author_name:** Development Team
- **author_email:** dev@agencia.com

### Architectural Decisions Provided by Starter

The Cookiecutter FastAPI starter establishes these foundational architectural decisions:

#### Language & Runtime Configuration

- **Python Version:** 3.10+ (aligns with FR requirements)
- **Async Runtime:** `asyncio` as default async execution model
- **Virtual Environment:** Standard Python venv pattern
- **Package Management:** pip/requirements.txt approach

#### Backend Framework

- **Primary Framework:** FastAPI (async web framework)
- **Request/Response:** Pydantic v2 for validation and serialization
- **ASGI Server:** Uvicorn for production serving
- **API Documentation:** Automatic OpenAPI generation (Swagger/ReDoc)

#### Database & ORM

- **Database:** PostgreSQL (configured by default)
- **Connection Pooling:** SQLAlchemy with connection pool
- **ORM:** SQLAlchemy ORM for data models
- **Migrations:** Alembic pre-configured for schema versioning
- **Initialization:** Database creation and migration scripts

#### Validation & Type Safety

- **Request Validation:** Pydantic v2 models for all API inputs
- **Type Hints:** Full Python type hint support throughout
- **Response Serialization:** Pydantic models for consistency
- **Custom Validators:** Built-in support for cross-field validation

#### Testing Infrastructure

- **Test Framework:** pytest
- **Async Testing:** pytest-asyncio for async test support
- **Test Structure:** tests/ directory with fixtures and conftest.py
- **Database Testing:** Test database configuration

#### Development Tools & Workflow

- **Code Formatting:** Black (standardized formatting)
- **Linting:** Flake8 (code quality)
- **Type Checking:** mypy (static type analysis)
- **Pre-commit Hooks:** Automated checks before commits
- **Development Server:** Auto-reload on file changes
- **Debugging:** VS Code debugger pre-configured

#### Environment & Configuration

- **Environment Variables:** `.env` file with python-dotenv
- **Settings Management:** Pydantic Settings for type-safe configuration
- **Environment Separation:** Development, testing, production configurations

#### Containerization & Deployment

- **Docker:** Dockerfile configured with Python 3.10, uvicorn
- **Multi-stage Builds:** Optimized image sizes
- **Kubernetes:** Example Helm charts for deployment
- **Health Checks:** HTTP health probe endpoint
- **Logging:** Structured logging configuration

#### Project Organization

**Directory Structure Established:**

```
ai_agent_framework/
├── backend/                      # Backend application
│   ├── app/
│   │   ├── api/                 # REST API endpoints
│   │   │   └── routes/          # Route modules
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── crud/                # Database CRUD operations
│   │   ├── core/                # Core utilities (config, security)
│   │   ├── db/                  # Database connection
│   │   └── main.py              # FastAPI app initialization
│   ├── alembic/                 # Database migrations
│   ├── tests/                   # Test suite
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile               # Container definition
│   └── .env                      # Environment variables
├── kubernetes/                   # Kubernetes manifests
│   ├── deployment.yaml
│   ├── service.yaml
│   └── values.yaml
├── docker-compose.yml            # Local development environment
└── .gitignore                    # Git configuration
```

### Key Dependencies Included

The starter pre-configures these dependencies:

- **FastAPI:** Modern async web framework
- **SQLAlchemy:** SQL toolkit and ORM
- **Pydantic:** Data validation using type hints
- **Alembic:** Database migration tool
- **Uvicorn:** ASGI server
- **psycopg2-binary:** PostgreSQL driver
- **python-dotenv:** Environment variable loading
- **pytest:** Testing framework

### Next Steps

**Project Initialization:**
The first implementation story should be running the Cookiecutter initialization command above, which creates the project scaffold with all architectural decisions established.

**What We're Not Re-deciding:**
The starter template establishes:
- Web framework choice (FastAPI)
- Async execution model
- ORM selection (SQLAlchemy)
- Database type (PostgreSQL)
- Configuration approach (environment-based)
- Deployment targets (Docker/Kubernetes ready)
- Testing framework (pytest)

**What We Still Need to Decide:**
The starter provides foundations, but we still need to make decisions on:
- API endpoint structure for agent interactions (FR81-FR90)
- Data model schemas for agents, sessions, messages (FR51-FR60)
- Authentication and authorization patterns (FR71-FR80)
- Logging and observability integration (FR61-FR70)
- Error handling and retry strategies (cross-cutting)
- LangChain integration points (FR31-FR40) via chat_models and agents
- Memory and context window strategies (FR41-FR50) via langchain.memory

These architectural decisions will be addressed in Step 04 (Core Architectural Decisions).

---

## Core Architectural Decisions

_All decisions made collaboratively through structured discovery and aligned with PRD requirements (90 FRs, 37 NFRs)._

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
These decisions must be implemented in MVP to deliver core functionality:

1. **Data Schema Design** - Foundation for all components
2. **API Authentication** - Required for security (FR71-80)
3. **Synchronous Chat Pattern** - Primary user interaction (FR81-90)
4. **LLM Error Handling** - Affects reliability and user experience
5. **Encryption Strategy** - LGPD compliance requirement

**Important Decisions (Shape Architecture):**
These decisions significantly influence architecture but have flexibility:

1. **Caching Strategy** - Performance optimization approach
2. **Message Retention** - Data lifecycle management
3. **Rate Limiting** - Cost control and abuse prevention
4. **Tool Execution Model** - Extensibility pattern
5. **Observability Implementation** - Operations and debugging

**Deferred Decisions (Post-MVP):**
These can be addressed in Growth phase without blocking MVP:

1. **Advanced Authorization (RBAC/Scopes)** - Simple API key sufficient for internal use
2. **Streaming Responses (SSE)** - Synchronous pattern meets <15s NFR for MVP
3. **Advanced Memory Summarization** - Rolling window sufficient initially
4. **Auto-retry with Fallback** - Fail-fast simpler, can add later
5. **Advanced CI/CD (Preview Environments)** - Basic GitHub Actions sufficient

---

### Category 1: Data Architecture

#### 1.1 Database Schema Design

**Decision:** Hybrid Relational + Strategic JSONB

**Rationale:**
- Relational core provides type safety, clear structure, IDE support (FR11-20 Developer Experience)
- Strategic JSONB enables flexibility for agent configs, tool metadata, memory strategies
- PostgreSQL JSONB indexing (GIN) provides performance when needed
- Aligns with SQLAlchemy ORM from Cookiecutter starter

**Implementation:**

```sql
-- Core Tables
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,  -- LLM provider, temperature, tools, retention policy
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agents(id),
    state VARCHAR(50) DEFAULT 'active',  -- active, completed, failed
    metadata JSONB,  -- Custom session data
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    role VARCHAR(20) NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    tool_calls JSONB,  -- Tool invocations and results
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE memory (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    strategy VARCHAR(50),  -- full, rolling, summary
    content JSONB NOT NULL,  -- Strategy-specific structure
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_sessions_agent_id ON sessions(agent_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_memory_session_id ON memory(session_id);
CREATE INDEX idx_agents_config_gin ON agents USING gin(config);
```

**Affects Components:**
- Memory & Context Management (FR41-50)
- Agent Execution Engine (FR51-60)
- REST API (FR81-90)
- Operations (FR91-100 - database migrations)

**Provided by Starter:** PostgreSQL, SQLAlchemy ORM, Alembic migrations ✅

---

#### 1.2 Caching Strategy

**Decision:** PostgreSQL Native + Connection Pooling Only

**Rationale:**
- MVP target: 10-20 simultaneous agents - PostgreSQL handles this load natively
- Stateless design doesn't require distributed cache across instances
- SQLAlchemy provides query-level caching and relationship lazy loading
- Connection pooling (default 20 connections) sufficient for MVP throughput
- Avoids additional infrastructure complexity and deployment overhead
- PostgreSQL optimization (indexes, query tuning) preferred over adding cache layer

**Implementation:**
- SQLAlchemy connection pool size: 20 (default)
- Pool timeout: 30s
- Pool recycle: 3600s (1 hour)
- Query-level caching via SQLAlchemy relationship lazy loading

**Performance Target:**
- API latency <500ms (excluding LLM) - NFR Performance
- Database queries <50ms average

**Affects Components:**
- REST API response times (FR81-90)
- Horizontal scaling approach (FR91-100)

**Future Consideration:** PostgreSQL read replicas or horizontal sharding if needed at scale (100+ agents)

---

#### 1.3 Message Retention Policy

**Decision:** Configurable Per Agent

**Rationale:**
- Different agent types have different retention needs
- Customer support agents: 90 days active retention
- Analytics agents: 30 days sufficient
- Compliance agents: indefinite retention
- Framework flexibility > one-size-fits-all policy

**Implementation:**

Agent config structure:
```json
{
  "retention_policy": {
    "enabled": true,
    "days": 90,
    "archive_strategy": "soft_delete"  // soft_delete, hard_delete, archive_table
  }
}
```

Background job (cron):
- Runs daily
- Checks agent retention policies
- Archives/deletes messages older than retention period
- Logs cleanup operations for audit

**Affects Components:**
- Memory & Context (FR41-50)
- Operations (FR91-100 - background jobs)
- Security & Compliance (FR71-80 - data lifecycle)

**MVP Implementation:** Retention config structure only, background job deferred to Growth phase

---

### Category 2: Authentication & Security

#### 2.1 API Authentication Method

**Decision:** API Key Authentication (X-API-Key header)

**Rationale:**
- Stateless, aligns with application design (FR91-100)
- Simple rotation and revocation
- Ideal for service-to-service authentication (primary use case)
- FastAPI security utilities support API keys natively
- Internal use first, then client projects - API keys sufficient

**Implementation:**

```python
# FastAPI dependency
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    # Verify against database or environment
    if not is_valid_api_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key
```

API Key storage:
- Hashed in database (bcrypt)
- Environment variables for system keys
- Rotation capability via management API

**Security Properties:**
- HTTPS/TLS required (all traffic encrypted)
- API keys hashed at rest
- Rate limiting per key (see 2.3)

**Affects Components:**
- REST API (FR81-90 - all endpoints protected)
- Security & Compliance (FR71-80)

**Provided by Starter:** FastAPI Security utilities ✅

---

#### 2.2 Authorization Model

**Decision:** Full Access Per API Key (MVP)

**Rationale:**
- Internal use: trusted developers, full access appropriate
- Simplicity > premature authorization complexity
- Can add scopes/RBAC in Growth phase when multi-tenant or client access needed

**Implementation:**
- Each valid API key = full access to all agents, sessions, operations
- Audit logging tracks which key performed which action
- Future: add `scopes` field to API key model for granular permissions

**Migration Path (Growth Phase):**
```python
# Future scopes
api_key.scopes = ["agents:read", "agents:write", "sessions:read"]
```

**Affects Components:**
- REST API (FR81-90 - endpoint protection)
- Observability (FR61-70 - audit logging)

**Deferred:** RBAC, scopes, role-based permissions (Growth phase)

---

#### 2.3 Rate Limiting Strategy

**Decision:** Dual Rate Limiting (Requests/min + Cost Tracking)

**Rationale:**
- Requests/min prevents API abuse (FR71-80 Security)
- Cost tracking prevents budget overruns from LLM usage
- Dual approach provides comprehensive protection

**Implementation:**

**Request Rate Limiting:**
- FastAPI middleware (slowapi or custom)
- Per API key: 60 requests/minute (configurable)
- HTTP 429 response when exceeded
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

**Cost Tracking:**
- Track tokens consumed per API key
- LangChain callbacks provide token counts per call via `get_openai_callback()`
- Database table: api_key_usage (key_id, tokens_used, cost_usd, timestamp)
- Alert when approaching budget threshold
- Optional: hard limit blocks requests when budget exceeded

```python
# Example cost tracking
class APIKeyUsage(Base):
    id: int
    api_key_id: int
    tokens_used: int
    cost_usd: Decimal
    provider: str  # openai, anthropic, azure
    timestamp: datetime
```

**Dashboard:** 
- Real-time usage metrics (FR61-70 Observability)
- Cost per API key
- Trend analysis

**Affects Components:**
- REST API (FR81-90 - middleware)
- LLM Integration (FR31-40 - token tracking)
- Observability (FR61-70 - metrics dashboard)

**Provided by Starter:** FastAPI middleware support ✅

---

#### 2.4 Data Encryption Strategy

**Decision:** Full Database Encryption (at-rest) + TLS (in-transit)

**Rationale:**
- LGPD compliance requirement (FR71-80 Security & Compliance)
- Defense in depth: encrypt at rest AND in transit
- Cloud-managed KMS reduces operational complexity
- PII protection built into foundation

**Implementation:**

**At-Rest Encryption:**
- PostgreSQL with encryption enabled (GCP Cloud SQL automatic encryption)
- Cloud KMS for key management (Google Cloud KMS)
- No application-level field encryption in MVP (can add for specific PII fields later)

**In-Transit Encryption:**
- HTTPS/TLS 1.3 for all API traffic
- PostgreSQL SSL connections
- LLM provider APIs (OpenAI, Anthropic) use HTTPS

**Configuration:**
```yaml
# Database connection
database:
  ssl_mode: require
  ssl_cert: /path/to/cert.pem
  ssl_key: /path/to/key.pem
```

**PII Detection (FR78):**
- Future: Presidio or similar for PII detection/masking
- MVP: Manual PII handling guidelines for developers

**Affects Components:**
- Security & Compliance (FR71-80)
- Database infrastructure (FR91-100)
- REST API (all traffic encrypted)

**Provided by Starter:** TLS configuration support ✅

---

### Category 3: API & Communication Patterns

#### 3.1 Agent Interaction Pattern

**Decision:** Synchronous Request-Response (POST /chat)

**Rationale:**
- NFR: <15s with planning, most cases <3s - synchronous feasible
- Simplest for clients to consume (no polling, no webhooks)
- FastAPI async/await handles concurrent requests efficiently
- Meets 10-20 concurrent agents target without async job queue

**Implementation:**

```python
@router.post("/agents/{agent_id}/chat")
async def chat(
    agent_id: int,
    message: ChatRequest,
    api_key: str = Depends(verify_api_key)
):
    # 1. Validate agent exists
    # 2. Load session context from PostgreSQL
    # 3. Call LLM via LangChain chat_models (async)
    # 4. Execute tools if needed via LangChain tools (async)
    # 5. Save message to database
    # 6. Return response
    return ChatResponse(
        response="...",
        metadata={
            "trace_id": "...",
            "tokens_used": 150,
            "latency_ms": 234
        }
    )
```

**Request:**
```json
POST /agents/123/chat
{
  "session_id": "abc-123",  // optional, creates new if omitted
  "message": "What's the weather?",
  "context": {}  // optional additional context
}
```

**Response:**
```json
{
  "response": "The current weather is...",
  "session_id": "abc-123",
  "metadata": {
    "trace_id": "trace-xyz-789",
    "tokens_used": 150,
    "latency_ms": 234,
    "llm_provider": "openai"
  }
}
```

**Timeout Handling:**
- FastAPI request timeout: 30s (configurable)
- If LLM exceeds timeout, return 504 Gateway Timeout
- Client can retry with same session_id

**Affects Components:**
- REST API (FR81-90)
- Agent Execution Engine (FR51-60)
- LLM Integration (FR31-40)

**Deferred:** Streaming responses (SSE), async job pattern (Growth phase if needed)

---

#### 3.2 Error Handling & Retry Strategy

**Decision:** Fail Fast (Client-Side Retry)

**Rationale:**
- Transparency: client knows immediately when failure occurs
- Control: client decides retry logic, timeout, fallback
- Simplicity: no server-side retry state management
- Debugging: clear error responses aid troubleshooting

**Implementation:**

**Error Response Format:**
```json
{
  "error": {
    "code": "LLM_TIMEOUT",
    "message": "OpenAI request timed out after 20s",
    "details": {
      "provider": "openai",
      "model": "gpt-4",
      "trace_id": "trace-xyz-789"
    },
    "retryable": true
  }
}
```

**HTTP Status Codes:**
- 400: Client error (bad request, validation failed)
- 401/403: Authentication/authorization failed
- 429: Rate limit exceeded (retryable after delay)
- 500: Internal server error
- 502: LLM provider error (retryable)
- 504: Timeout (retryable)

**Error Categories:**
- `LLM_TIMEOUT`: LLM provider timeout
- `LLM_RATE_LIMIT`: Provider rate limit
- `LLM_INVALID_REQUEST`: Bad prompt/parameters
- `TOOL_EXECUTION_FAILED`: Tool error
- `DATABASE_ERROR`: Database connection/query error
- `VALIDATION_ERROR`: Request validation failed

**Logging:**
All errors logged with trace_id for debugging (FR61-70)

**Affects Components:**
- REST API (FR81-90)
- LLM Integration (FR31-40)
- Tool/Plugin System (FR21-30)
- Observability (FR61-70)

**Future Consideration:** Optional server-side retry with exponential backoff (configurable per agent)

---

#### 3.3 Tool Execution Model

**Decision:** Configurable Sync/Async per Tool

**Rationale:**
- Fast tools (calculations, lookups): synchronous execution, no overhead
- Slow tools (API calls, file I/O): async execution, non-blocking
- Developer decides per tool based on characteristics
- Maximum flexibility without forcing all-async complexity

**Implementation:**

```python
# Decorator with async flag
@tool(async_execution=False)
def calculate_sum(a: int, b: int) -> int:
    """Fast synchronous tool"""
    return a + b

@tool(async_execution=True)
async def fetch_weather(city: str) -> dict:
    """Slow async tool - API call"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.weather.com/{city}")
        return response.json()
```

**Execution Logic:**
```python
# Agent execution engine
for tool_call in agent_response.tool_calls:
    tool = registry.get_tool(tool_call.name)
    
    if tool.async_execution:
        result = await tool.execute(**tool_call.args)
    else:
        result = tool.execute(**tool_call.args)
    
    tool_results.append(result)
```

**Tool Registry:**
- Decorator registers tools with metadata
- Registry tracks: name, description, parameters, async flag
- Discovery via `@tool` decorator (FR21-30)

**Error Handling:**
- Tool exceptions caught and returned to agent
- Agent decides how to proceed (retry, fallback, inform user)

**Affects Components:**
- Tool/Plugin System (FR21-30)
- Agent Execution Engine (FR51-60)
- Developer Experience (FR11-20)

**Provided by Starter:** Python async/await support ✅

---

#### 3.4 Observability in API Responses

**Decision:** Detailed Debug Information Always Available

**Rationale:**
- Framework for developers: observability aids debugging (FR11-20)
- Detailed metadata supports troubleshooting production issues
- Transparency builds trust
- Performance tracking via response metadata

**Implementation:**

**Standard Response (always included):**
```json
{
  "response": "...",
  "metadata": {
    "trace_id": "trace-abc-123",
    "session_id": "session-xyz-789",
    "tokens_used": 150,
    "latency_ms": 234,
    "llm_provider": "openai",
    "model": "gpt-4-turbo",
    "timestamp": "2026-01-13T10:30:00Z"
  }
}
```

**Debug Mode (query param: ?debug=true):**
```json
{
  "response": "...",
  "metadata": {...},
  "debug": {
    "reasoning_steps": [
      "Analyzed user question",
      "Identified need for weather tool",
      "Called fetch_weather tool",
      "Synthesized response"
    ],
    "tools_called": [
      {
        "name": "fetch_weather",
        "args": {"city": "São Paulo"},
        "result": {"temp": 28, "condition": "sunny"},
        "latency_ms": 123
      }
    ],
    "context_window": {
      "messages_count": 5,
      "tokens_total": 450,
      "strategy": "rolling"
    },
    "database_queries": 3,
    "cache_hits": 2
  }
}
```

**Trace ID Propagation:**
- Generated at request entry
- Propagated through all components
- Logged in all operations
- Returned in response and errors
- Enables end-to-end tracing (FR61-70)

**Affects Components:**
- REST API (FR81-90)
- Observability (FR61-70)
- Developer Experience (FR11-20)

---

### Category 4: Infrastructure & Deployment

#### 4.1 Observability Implementation

**Decision:** Python Logging + Stdout (Structured JSON)

**Rationale:**
- Kubernetes/Docker best practice: logs to stdout/stderr
- Container orchestration captures logs automatically
- Simple, no external dependencies for MVP
- Can aggregate to ELK, Loki, or CloudWatch later

**Implementation:**

**Logging Configuration:**
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "trace_id": getattr(record, 'trace_id', None),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logging.getLogger().handlers[0].setFormatter(JSONFormatter())
```

**Log Levels:**
- DEBUG: Detailed execution flow (dev only)
- INFO: Request/response, tool calls, LLM interactions
- WARNING: Retry attempts, degraded performance
- ERROR: Exceptions, failed requests
- CRITICAL: System failures

**Trace ID Context:**
```python
# FastAPI middleware adds trace_id to all logs
@app.middleware("http")
async def add_trace_id(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
    request.state.trace_id = trace_id
    
    # Add trace_id to logging context
    with logging_context(trace_id=trace_id):
        response = await call_next(request)
    
    response.headers["X-Trace-ID"] = trace_id
    return response
```

**Affects Components:**
- Observability (FR61-70)
- All components (logging throughout)
- Operations (FR91-100 - troubleshooting)

**Provided by Starter:** Python logging module ✅

**Future:** Add Prometheus /metrics endpoint, OpenTelemetry tracing (Growth phase)

---

#### 4.2 CI/CD Pipeline

**Decision:** GitHub Actions (Basic - Tests on PR, Manual Deploy)

**Rationale:**
- Simplicity for MVP: automated tests, controlled deployments
- GitHub Actions integrated with repository
- Manual deployment approval prevents accidental production changes
- Can automate deployments later when processes mature

**Implementation:**

**GitHub Actions Workflow:**
```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: pytest --cov=app tests/
      - name: Lint
        run: |
          flake8 app/
          mypy app/
  
  deploy-dev:
    needs: test
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Dev
        run: echo "Manual deployment trigger required"
        # Future: kubectl apply or helm upgrade
```

**Deployment Process:**
1. PR created → Tests run automatically
2. PR merged to `develop` → Manual trigger to deploy to dev environment
3. `develop` merged to `main` → Manual trigger to deploy to staging/production

**Environments:**
- **Development:** Auto-deploy on merge to develop (future)
- **Staging:** Manual deploy from main branch
- **Production:** Manual deploy with approval

**Affects Components:**
- Operations (FR91-100)
- Testing infrastructure (pytest from starter)

**Provided by Starter:** pytest, pre-commit hooks ✅

**Future:** Auto-deploy to dev, preview environments for PRs (Growth phase)

---

#### 4.3 Horizontal Scaling Strategy

**Decision:** Kubernetes HPA (CPU/Memory-Based Autoscaling)

**Rationale:**
- Stateless design enables seamless horizontal scaling (FR91-100)
- K8s HPA is industry standard
- CPU/memory metrics sufficient for MVP workload
- Simple configuration, automatic operation

**Implementation:**

**Kubernetes HPA Configuration:**
```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-agent-framework-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-agent-framework
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min cooldown
    scaleUp:
      stabilizationWindowSeconds: 60   # 1 min warmup
```

**Scaling Triggers:**
- CPU > 70% → scale up
- Memory > 80% → scale up
- CPU < 50% for 5 minutes → scale down

**Stateless Requirements:**
- All state in PostgreSQL (sessions, messages, agents)
- No in-memory session storage
- Connection pooling per instance
- Load balancer distributes traffic (K8s Service)

**Database Considerations:**
- PostgreSQL connection limit: 100
- Each pod: 20 connections max
- Max 5 pods simultaneously (100/20)
- HPA maxReplicas: 10, but connection pooling prevents overload

**Affects Components:**
- Operations (FR91-100 - scaling strategy)
- REST API (stateless design)
- Database (connection pooling)

**Provided by Starter:** Docker, Kubernetes manifests ✅

**MVP Config:** 2-4 replicas for 10-20 agents
**12-Month Target:** 5-10 replicas for 100+ agents

---

### Decision Impact Analysis

#### Implementation Sequence (Recommended Order)

**Phase 1: Foundation (Week 1-2)**
1. Database schema (migrations via Alembic)
2. SQLAlchemy models with Pydantic validation
3. API Key authentication middleware
4. Basic logging configuration (JSON to stdout)

**Phase 2: Core Features (Week 3-6)**
5. LLM integration via LangChain (ChatOpenAI, ChatAnthropic)
6. Synchronous `/chat` endpoint with async LLM calls
7. Tool registry via `@tool` decorator from LangChain and execution (sync/async)
8. Session and message storage with langchain.memory integration
9. Error handling and standardized responses

**Phase 3: Security & Observability (Week 7-8)**
10. Rate limiting middleware (requests/min)
11. Cost tracking (token usage per API key)
12. TLS/HTTPS configuration
13. Database encryption (Cloud SQL settings)
14. Trace ID propagation
15. Debug mode responses

**Phase 4: Operations (Week 9-12)**
16. GitHub Actions CI (tests on PR)
17. Docker image optimization
18. Kubernetes deployment manifests
19. HPA configuration
20. Manual deployment process documentation
21. Monitoring dashboard (basic metrics)

#### Cross-Component Dependencies

**Database Schema → All Components**
- REST API needs schema for sessions/messages
- Memory management needs schema for context storage
- Tool system needs schema for tool metadata
- Observability needs schema for audit logs

**API Authentication → All Endpoints**
- Every REST endpoint protected by API key
- Rate limiting tied to API key
- Cost tracking tied to API key
- Audit logging includes API key identifier

**Trace ID → Observability**
- Generated at API entry
- Propagated through LLM calls
- Included in all logs
- Returned in responses and errors
- Enables end-to-end debugging

**LiteLLM Integration → Agent Execution**
- Execution engine calls LiteLLM
- Tool results fed back to LLM
- Token tracking for cost management
- Provider abstraction enables fallback (future)

**Stateless Design → Scaling**
- No in-memory state enables HPA
- Database handles all persistence
- Load balancer distributes requests
- Each pod independent

---

### Alignment with PRD Requirements

**Functional Requirements Coverage:**

- ✅ FR1-10 (Framework Core): Schema, config in database, environment-based settings
- ✅ FR11-20 (Agent Development): SQLAlchemy models, Pydantic validation, type hints
- ✅ FR21-30 (Tool/Plugin System): Decorator registration, sync/async configurable
- ✅ FR31-40 (LLM Integration): LangChain chat_models, token tracking via callbacks, cost monitoring
- ✅ FR41-50 (Memory & Context): PostgreSQL storage, configurable retention
- ✅ FR51-60 (Execution & Reasoning): Synchronous chat pattern, tool execution
- ✅ FR61-70 (Observability): JSON logging, trace IDs, debug responses, metrics tracking
- ✅ FR71-80 (Security & Compliance): API keys, rate limiting, encryption, LGPD compliance
- ✅ FR81-90 (REST API): POST /chat, session management, OpenAPI (FastAPI auto-gen)
- ✅ FR91-100 (Operations): Docker, K8s, HPA, stateless design, Alembic migrations

**Non-Functional Requirements Coverage:**

- ✅ Performance: <3s simple, <15s planning (synchronous pattern supports this)
- ✅ Security: API keys, encryption, rate limiting, HTTPS/TLS
- ✅ Scalability: Stateless design, HPA, connection pooling, 10-20 agents MVP
- ✅ Integration: LangChain provider abstraction via BaseChatModel, native tool system extensibility
- ✅ Maintainability: SQLAlchemy models, Pydantic validation, structured logging

---

### Technology Versions (Verified 2026-01-13)

**Core Stack (from Cookiecutter Starter):**
- Python: 3.10+
- FastAPI: Latest stable (0.109.0+)
- PostgreSQL: 15+ (Cloud SQL or self-hosted)
- SQLAlchemy: 2.0+
- Pydantic: 2.0+
- Alembic: Latest (1.13+)
- Uvicorn: Latest (0.27+)

**Additional Dependencies:**
- LangChain: Latest stable (≥0.1.0) (for LLM abstraction, agents, tools, memory)
- LangChain-OpenAI: Latest (OpenAI integration)
- LangChain-Anthropic: Latest (Anthropic integration)
- python-dotenv: Latest (environment variables)
- pytest: 7.4+ (testing with TDD approach)
- pytest-bdd: Latest (BDD scenarios)
- pytest-asyncio: Latest (async testing)
- httpx: Latest (async HTTP for tools)

**Infrastructure:**
- Docker: 24+
- Kubernetes: 1.28+
- GitHub Actions: N/A (cloud service)

---

