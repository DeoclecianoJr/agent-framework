---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments: 
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/epics.md'
status: 'Epic 7 (RAG) Complete - Ready for Implementation'
---

# ai_framework - Epic Breakdown (RAG Edition)

## Overview

This document provides the complete epic and story breakdown for **AI Agent Framework**, decomposing the requirements from the PRD and Architecture into implementable stories. This version includes the new **RAG (Retrieval-Augmented Generation)** capability with Google Drive and SharePoint integration.

**Last Updated:** 2026-01-27  
**Total FRs:** 100  
**Total NFRs:** 44  

---

## Requirements Inventory

### Functional Requirements (100 Total)

**FR1-FR10: Core Framework (10 requirements)**
- FR1: PyPI installation with dependencies
- FR2: Global .env configuration for framework settings
- FR3: Environment variable overrides
- FR4: Support for multiple environments (dev, staging, prod)
- FR5: Inline agent configuration via @agent decorator
- FR6: Hot reload in development mode
- FR7: Sensible defaults for all settings
- FR8: Configuration validation on startup
- FR9: Error messages for invalid config
- FR10: Configuration documentation

**FR11-FR20: Agent Development (10 requirements)**
- FR11: Agent template creation (example agents)
- FR12: Agent customization via inline config in @agent decorator
- FR13: Local testing tools
- FR14: CLI playground for interactive testing
- FR15: Clear error feedback during development
- FR16: Full type hints for IDE autocomplete
- FR17: Agent registration system via decorators
- FR18: Multi-agent support in same runtime
- FR19: Agent lifecycle hooks (startup, shutdown)
- FR20: Agent metadata (name, description, version)

**FR21-FR30: Tools/Plugins (10 requirements)**
- FR21: Tool decorator registration (`@tool`)
- FR22: Parameter validation via type hints
- FR23: Automatic tool discovery
- FR24: Class-based tool extension
- FR25: Tool execution hooks (pre/post)
- FR26: Tool parameter passing
- FR27: Tool error handling
- FR28: Tool timeout protection
- FR29: Parallel tool execution
- FR30: Tool registry management

**FR31-FR40: LLM Integration (10 requirements)**
- FR31: OpenAI provider support
- FR32: Anthropic provider support
- FR33: Azure OpenAI support
- FR34: Provider switching via config
- FR35: LLM abstraction layer
- FR36: Automatic retry logic
- FR37: Provider fallback mechanism
- FR38: Mock LLM for development/testing
- FR39: Token counting and tracking
- FR40: Cost estimation per request

**FR41-FR50: Memory & Context (10 requirements)**
- FR41: PostgreSQL persistence for sessions
- FR42: Message history retrieval
- FR43: Full context strategy
- FR44: Rolling window strategy
- FR45: Summarization strategy
- FR46: Memory strategy configuration per agent
- FR47: Automatic context window management
- FR48: Session persistence across restarts
- FR49: Custom memory strategy extension
- FR50: Context pruning when limit exceeded

**FR51-FR60: Execution & Reasoning (10 requirements)**
- FR51: User message processing
- FR52: Tool execution decision making
- FR53: Tool execution with results
- FR54: Response generation
- FR55: Context maintenance during conversation
- FR56: Guardrails application
- FR57: Response grounding in data
- FR58: Fallback to "I don't know"
- FR59: Chain-of-thought planning mode
- FR60: Multi-turn conversation handling

**FR61-FR70: Observability (10 requirements)**
- FR61: Structured JSON logging
- FR62: Distributed trace IDs
- FR63: Debug mode with verbose logging
- FR64: Metrics dashboard
- FR65: Log filtering by severity
- FR66: Prometheus metrics export
- FR67: Request profiling
- FR68: Performance alerts
- FR69: Error rate tracking
- FR70: Custom metrics injection

**FR71-FR80: Security & Compliance (10 requirements)**
- FR71: API key generation and management
- FR72: Encryption at rest (AES-256)
- FR73: HTTPS/TLS enforcement
- FR74: PII detection in messages
- FR75: Automatic PII masking
- FR76: Immutable audit logs
- FR77: Rate limiting per API key
- FR78: Content moderation
- FR79: Configurable guardrails per agent
- FR80: LGPD compliance (deletion, export, retention)

**FR81-FR90: API & Operations (10 requirements)**
- FR81: POST /chat - Start new chat session
- FR82: GET /chat/{session_id} - Get session details
- FR83: DELETE /chat/{session_id} - Delete session
- FR84: Health check endpoint
- FR85: Metrics endpoint
- FR86: Input validation on all endpoints
- FR87: Consistent error handling
- FR88: OpenAPI/Swagger documentation
- FR89: Production Dockerfile
- FR90: Helm chart for GKE deployment

**FR91-FR100: RAG & Knowledge Base (10 requirements)**
- FR91: Configure Google Drive folder or SharePoint site as knowledge source per agent
- FR92: OAuth 2.0 authentication flow for Google Drive and SharePoint access
- FR93: Scheduled batch sync (every 24h) fetches new/modified documents from cloud sources
- FR94: Change detection using Drive API changeToken or SharePoint delta queries
- FR95: Document parsing supports PDF, TXT, Markdown, DOCX, Google Docs, Office files
- FR96: Automatic embedding generation for synced documents with chunking strategy
- FR97: Each agent has isolated knowledge base and vector store
- FR98: Semantic search retrieves relevant chunks during chat runtime with metadata filtering
- FR99: Manual sync trigger via API endpoint for immediate indexation
- FR100: Knowledge base status tracking (last sync, document count, embedding count, errors)

---

### Non-Functional Requirements (44 Total)

**Performance (10 NFRs)**
- NFR1: Chat response < 3s (simple queries)
- NFR2: Chat response < 15s (with planning/tools)
- NFR3: RAG semantic search < 300ms for top-k retrieval
- NFR4: Document indexing batch < 1 hour for 1000 documents
- NFR5: API latency < 500ms
- NFR6: Dashboard load < 2s
- NFR7: Logging overhead < 50ms per entry
- NFR8: Support 100+ concurrent calls
- NFR9: < 500MB memory per agent (excluding vector store)
- NFR10: Vector store < 2GB per agent for 10k chunks

**Security & Compliance (9 NFRs)**
- NFR11: AES-256 encryption at rest
- NFR12: TLS 1.2+ for all communications
- NFR13: API keys masked in logs
- NFR14: LGPD deletion complete < 24 hours
- NFR15: Audit log retention ≥ 90 days
- NFR16: Max 1000 requests/hour per key (configurable)
- NFR17: > 90% PII detection accuracy
- NFR18: > 95% content moderation recall
- NFR19: API key rotation without downtime

**Scalability (9 NFRs)**
- NFR20: Horizontal scaling without reconfiguration
- NFR21: MVP supports 10-20 agents
- NFR22: 12-month target: 100+ agents
- NFR23: PostgreSQL single instance (MVP), replication later
- NFR24: < 10% latency increase at 10x load
- NFR25: Stateless design for scaling
- NFR26: Efficient connection pooling
- NFR27: Support up to 10k documents per agent knowledge base (MVP)
- NFR28: pgvector indexes for efficient similarity search

**Integration & Reliability (9 NFRs)**
- NFR29: Automatic LLM provider fallback
- NFR30: 3 retries with exponential backoff for all external APIs
- NFR31: ACID transactions for data integrity
- NFR32: Circuit breakers for cloud storage APIs
- NFR33: OAuth token refresh automatic retry on 401 errors
- NFR34: 99% uptime target
- NFR35: Recovery without data loss
- NFR36: Structured failure logging
- NFR37: Graceful degradation if Drive/SharePoint unavailable

**Maintainability (7 NFRs)**
- NFR38: ≥80% test coverage
- NFR39: 100% public API type hints
- NFR40: Docstrings for all modules
- NFR41: Dependency version pinning
- NFR42: CI/CD pipeline < 5 minutes
- NFR43: Versioned automatic migrations
- NFR44: Breaking changes in major versions only

---

### Additional Requirements from Architecture

**Starter Template:**
- Use Cookiecutter FastAPI template as foundation
- PostgreSQL with SQLAlchemy ORM
- Alembic for migrations
- FastAPI async/await pattern

**Technical Stack Decisions:**
- LangChain for LLM abstraction
- PostgreSQL with pgvector extension (unified data + vector store)
- Google Drive API and Microsoft Graph API for RAG
- APScheduler for batch jobs
- Prometheus for metrics

**Architecture Patterns:**
- Stateless API design
- Repository pattern for data access
- Factory pattern for provider abstraction
- Strategy pattern for memory management
- Observer pattern for event hooks

---

## Epic List

**Análise de Status - Comparação com Épicos Existentes:**

Baseado em:
- [epics.md](/home/wbj-compassuol-010/Documents/projects/ai_framework/_bmad-output/planning-artifacts/epics.md) (épicos anteriores com 6 épicos)
- [week-1-completion-report.md](/home/wbj-compassuol-010/Documents/projects/ai_framework/week-1-completion-report.md) (Week 1 completa)
- Código fonte atual (support_agent.py, ai_framework/, app/)

### ✅ Já Implementado (Épicos 1-6 do documento anterior):

**Epic 1: Foundation Infrastructure & Developer Setup** ✅ COMPLETO
- Week 1 tasks 1.1-1.5 implementadas e testadas (28/28 testes passando)
- FR1-FR10, FR87, FR91-FR96 cobertos

**Epic 2: SDK Development Experience** ✅ COMPLETO
- @agent decorator funcional (examples/support_agent.py)
- @tool decorator implementado
- FR11-FR20 cobertos

**Epic 3: Runtime Chat API** ✅ COMPLETO
- POST /chat, GET /chat/{session_id}, /chat/{session_id}/messages
- Session management implementado
- FR81-FR86, FR41-FR47 cobertos

**Epic 4: LLM Integration & Memory** ✅ COMPLETO
- OpenAI, Anthropic, Google Gemini, Phi3 (Ollama) implementados
- SummaryMemory, BufferMemory, RollingWindow strategies
- Token counting, cost tracking
- FR31-FR40, FR48-FR50 cobertos

**Epic 5: Tools & Agent Capabilities** ✅ PARCIAL
- Tool registry, decorator, validation funcionando
- Guardrails implementados (blocklist, allowlist, theme filtering)
- FR21-FR30, FR51-FR60 parcialmente cobertos

**Epic 6: Production Operations & Security** ✅ PARCIAL
- Structured logging, trace IDs, metrics (Prometheus)
- API key auth, PII detection, rate limiting
- Audit logs, encryption
- FR61-FR80 parcialmente cobertos

---

### ❌ NOVO - Precisa Implementar (RAG):

**Epic 7: RAG & Knowledge Base com Google Drive/SharePoint** ❌ NÃO IMPLEMENTADO

Este é o **ÚNICO épico novo** que precisa ser criado com user stories completas:

1. **Epic 7: RAG & Knowledge Base** (FR91-FR100) ⭐ **NOVO**
   - Google Drive OAuth 2.0 integration
   - SharePoint/Microsoft Graph API integration
   - PostgreSQL pgvector extension setup
   - Document sync scheduler (APScheduler 24h)
   - Document loaders (PDF, TXT, Markdown, DOCX, Google Docs, Office)
   - Embedding generation (OpenAI Embeddings ou Sentence-Transformers)
   - Vector storage and indexing
   - Semantic search integration in chat runtime
   - Knowledge base isolation per agent
   - API endpoints para gestão de conhecimento

---

## Decisão: Criar APENAS Epic 7 (RAG)

Este PRD com RAG resultará em **1 épico novo apenas**:

1. ~~**Epic 1-6: Foundation → Security**~~ ✅ JÁ IMPLEMENTADOS (ver epics.md anterior)
2. **Epic 7: RAG & Knowledge Base** (FR91-FR100) ⭐ **CRIAR AGORA**

---

## Epic 7: RAG & Knowledge Base

**Goal:** Agents can retrieve and use information from cloud-stored documents (Google Drive, SharePoint) to ground responses in organizational knowledge, with support for multiple LLM providers (OpenAI, Gemini, Phi3:mini local).

**FRs Covered:** FR91-FR100  
**NFRs Covered:** NFR3, NFR4, NFR27, NFR28, NFR32, NFR33, NFR37

**Architecture:**
- PostgreSQL with pgvector extension for vector storage
- Embedding provider abstraction (OpenAI Embeddings, Google Vertex AI, Sentence-Transformers local)
- Google Drive API and Microsoft Graph API for document sync
- APScheduler for scheduled batch processing (24h intervals)
- LangChain Document Loaders for parsing
- Cosine similarity search via pgvector

---

### Story 7.1: PostgreSQL pgvector Extension Setup

As a developer,
I want pgvector extension installed and configured in PostgreSQL,
So that I can store and search vector embeddings efficiently alongside relational data.

**Acceptance Criteria:**

**Given** PostgreSQL database is running
**When** I run database migrations
**Then** pgvector extension is enabled (`CREATE EXTENSION IF NOT EXISTS vector`)
**And** `knowledge_documents` table is created with vector column
**And** IVFFlat or HNSW index is created on embedding column for fast similarity search
**And** table schema includes: id, agent_id, source_type, source_id, file_name, content_chunk, embedding (vector), metadata (JSONB), created_at
**And** table has foreign key to agents table with cascade delete
**And** I can query vectors using cosine distance operator `<=>` successfully

---

### Story 7.2: Embedding Provider Abstraction (LangChain)

As a developer,
I want to use LangChain Embeddings abstraction for generating embeddings,
So that RAG works consistently across all LLM providers (OpenAI, Gemini, Phi3/Ollama) with minimal configuration.

**Acceptance Criteria:**

**Given** I have configured an LLM provider via `.env` (AI_SDK_LLM_PROVIDER=openai|gemini|ollama)
**When** the system initializes RAG embedding generation
**Then** the appropriate LangChain Embeddings class is instantiated:
- `openai` → `langchain_openai.OpenAIEmbeddings(model="text-embedding-3-small")`
- `gemini` → `langchain_google_genai.GoogleGenerativeAIEmbeddings(model="models/embedding-001")`
- `ollama` → `langchain_ollama.OllamaEmbeddings(model="nomic-embed-text")` for local Phi3
**And** all embedding providers use consistent LangChain interface:
- `.embed_query(text: str)` for single queries (chat messages)
- `.embed_documents(texts: List[str])` for batch document processing
**And** configuration includes environment variables for API keys and model selection
**And** embeddings respect provider rate limits with LangChain's built-in retry logic
**And** embedding dimensions are consistent per provider (can query via `.embed_query("test").shape`)
**And** system falls back to HuggingFaceEmbeddings (local, free) if API provider fails or is unavailable
**And** embedding provider selection is logged for observability

---

### Story 7.3: Google Drive OAuth 2.0 Integration

As an agent administrator,
I want to authenticate with Google Drive using OAuth 2.0,
So that agents can access documents stored in Google Drive folders securely.

**Acceptance Criteria:**

**Given** I want to configure Google Drive as a knowledge source
**When** I initiate OAuth flow via API endpoint POST `/agents/{agent_id}/knowledge/sources`
**Then** system redirects me to Google consent screen
**And** I grant permissions for Drive API read access
**And** system receives authorization code and exchanges for access + refresh tokens
**And** tokens are encrypted (AES-256) and stored in database linked to agent
**And** refresh token is automatically used to renew access token before expiry
**And** OAuth flow handles errors gracefully (user denial, network issues)
**And** I can configure specific folder IDs or shared drives as knowledge sources

---

### Story 7.4: SharePoint/Microsoft Graph API OAuth Integration

As an agent administrator,
I want to authenticate with SharePoint using Microsoft Graph API,
So that agents can access documents stored in SharePoint sites and OneDrive.

**Acceptance Criteria:**

**Given** I want to configure SharePoint as a knowledge source
**When** I initiate OAuth flow via API endpoint POST `/agents/{agent_id}/knowledge/sources`
**Then** system redirects me to Microsoft login and consent screen
**And** I grant permissions for Files.Read.All and Sites.Read.All
**And** system receives authorization code and exchanges for access + refresh tokens via MSAL library
**And** tokens are encrypted and stored securely in database
**And** refresh token automatically renews access token on 401 errors
**And** I can configure specific SharePoint site URLs, document libraries, or OneDrive folders
**And** system validates site permissions before storing configuration

---

### Story 7.5: Document Sync Scheduler (APScheduler 24h Batch)

As an agent administrator,
I want documents to be automatically synced from cloud sources every 24 hours,
So that the knowledge base stays up-to-date without manual intervention.

**Acceptance Criteria:**

**Given** I have configured one or more cloud sources (Drive/SharePoint) for an agent
**When** the scheduled sync job runs (every 24h via APScheduler)
**Then** job fetches list of files from each configured source
**And** uses Google Drive changeToken or SharePoint delta queries to detect only new/modified files since last sync
**And** downloads only changed documents (not all documents every time)
**And** parses documents using appropriate loader (PDF, TXT, Markdown, DOCX, Google Docs, Office files)
**And** chunks documents into smaller pieces (configurable size, e.g., 512 tokens with 50 token overlap)
**And** generates embeddings for each chunk using configured provider
**And** stores chunks and embeddings in `knowledge_documents` table with metadata (source, file_name, last_modified)
**And** job logs progress, errors, and completion status
**And** sync status is queryable via GET `/agents/{agent_id}/knowledge/status`
**And** job handles API rate limits with exponential backoff
**And** job respects NFR4: completes within 1 hour for 1000 documents

---

### Story 7.6: Document Parsing and Chunking

As a developer,
I want documents to be parsed and chunked intelligently,
So that semantic search retrieves relevant passages without overwhelming context.

**Acceptance Criteria:**

**Given** a document has been downloaded from Google Drive or SharePoint
**When** the system processes the document
**Then** correct document loader is selected based on file extension/MIME type:
- PDF → PyPDF2 or pdfplumber
- TXT/Markdown → direct text reading
- DOCX → python-docx
- Google Docs → export as plain text via Drive API
- Office files → python-pptx or openpyxl where applicable
**And** text is extracted successfully from document
**And** text is split into chunks using RecursiveCharacterTextSplitter (configurable chunk_size=512, chunk_overlap=50)
**And** each chunk retains metadata: source_type, source_id, file_name, page_number (if applicable), chunk_index
**And** chunks that are too short (< 50 chars) or too long (> 2000 chars) are handled appropriately
**And** extraction errors are logged but don't halt entire sync process

---

### Story 7.7: Agent-Specific Knowledge Base Isolation

As an agent administrator,
I want each agent to have its own isolated knowledge base,
So that agents don't cross-contaminate knowledge from different domains.

**Acceptance Criteria:**

**Given** I have multiple agents configured (e.g., `support_agent`, `sales_agent`)
**When** I configure knowledge sources for `support_agent`
**Then** documents synced for `support_agent` are stored with `agent_id = 'support_agent'`
**And** queries from `support_agent` only retrieve chunks where `agent_id = 'support_agent'`
**And** `sales_agent` cannot access `support_agent`'s knowledge base
**And** database indexes support efficient filtering by agent_id
**And** deletion of an agent cascades to delete all its knowledge documents
**And** agents can share same cloud source (folder/site) but maintain separate embeddings

---

### Story 7.8: Semantic Search Integration in Chat Runtime

As a user chatting with an agent,
I want the agent to automatically search its knowledge base when answering questions,
So that responses are grounded in organizational documents.

**Acceptance Criteria:**

**Given** an agent has a populated knowledge base with embeddings
**When** I send a message to the agent via POST `/chat/{session_id}/message`
**Then** system generates embedding for my message using the same provider as indexing
**And** performs cosine similarity search in `knowledge_documents` table filtered by agent_id
**And** retrieves top-k most similar chunks (configurable k=5, threshold=0.7 similarity)
**And** injects retrieved chunks as context in the LLM system prompt before user message
**And** LLM generates response using both retrieved knowledge and conversation history
**And** retrieved chunks metadata is included in response debug info (if debug mode enabled)
**And** semantic search completes in < 300ms (NFR3)
**And** if no relevant chunks found (all below threshold), agent responds without RAG context

---

### Story 7.9: Manual Sync Trigger API

As an agent administrator,
I want to manually trigger immediate document synchronization,
So that I don't have to wait 24 hours when I add new important documents.

**Acceptance Criteria:**

**Given** I have configured knowledge sources for an agent
**When** I call POST `/agents/{agent_id}/knowledge/sync`
**Then** system immediately starts a sync job for that agent (asynchronously)
**And** endpoint returns 202 Accepted with job_id
**And** I can poll sync status via GET `/agents/{agent_id}/knowledge/status?job_id={job_id}`
**And** status includes: state (pending/running/completed/failed), progress percentage, documents processed, errors
**And** manual sync follows same process as scheduled sync (change detection, parsing, embedding, storage)
**And** manual sync can be triggered while scheduled sync is disabled
**And** concurrent sync requests for same agent are queued (not run in parallel)

---

### Story 7.10: Knowledge Base Status and Management API

As an agent administrator,
I want to view and manage the knowledge base for each agent,
So that I can monitor sync health and troubleshoot issues.

**Acceptance Criteria:**

**Given** an agent has configured knowledge sources and synced documents
**When** I call GET `/agents/{agent_id}/knowledge/status`
**Then** I receive comprehensive status information:
- Last sync timestamp
- Next scheduled sync time
- Total documents indexed
- Total embedding count (chunks)
- Storage size (MB)
- Sync errors (if any) with error messages
- Per-source breakdown (Drive folder X: 50 docs, SharePoint site Y: 30 docs)
**And** when I call GET `/agents/{agent_id}/knowledge/documents`
**Then** I receive paginated list of indexed documents with metadata (file_name, source, last_modified, chunk_count)
**And** when I call DELETE `/agents/{agent_id}/knowledge/sources/{source_id}`
**Then** source configuration is removed and all related embeddings are deleted
**And** when I call GET `/agents/{agent_id}/knowledge/sources`
**Then** I see all configured sources (Google Drive folders, SharePoint sites) with OAuth status (active/expired)

---

## Testing Requirements for Epic 7

### Unit Tests
- Embedding provider selection logic (OpenAI, Gemini, Sentence-Transformers)
- Document chunking with overlap
- OAuth token encryption/decryption
- Vector similarity calculation
- Metadata filtering logic

### Integration Tests
- pgvector extension installation
- Full sync workflow (OAuth → download → parse → embed → store)
- Semantic search query with agent_id isolation
- APScheduler job execution
- API endpoint responses (POST /sources, GET /status, etc.)

### E2E Tests
- Complete flow: configure Drive source → OAuth → auto sync → chat uses RAG
- Manual sync trigger and status polling
- Multi-agent isolation (agent A can't see agent B's knowledge)
- Knowledge base deletion on agent deletion

### Performance Tests
- Semantic search < 300ms for top-k retrieval (NFR3)
- Batch indexing < 1 hour for 1000 documents (NFR4)
- pgvector index scan performance with 10k vectors

---

_Epic 7 user stories completas. Aguardando feedback ou comando para finalizar documento._
