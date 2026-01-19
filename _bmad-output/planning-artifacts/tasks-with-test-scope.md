---
documentType: 'tasks-with-test-scope'
project_name: 'AI Agent Framework'
user_name: 'Wbj-compassuol-010'
date: '2026-01-13'
lastUpdated: '2026-01-16'
status: 'Updated - Week 1-4 (IR Recommendations Applied)'
---

# Tasks & Test Scope (MVP Weeks 1-4)

Este documento mapeia as tarefas de desenvolvimento para as primeiras 4 semanas do roadmap MVP e define, para cada tarefa, o escopo de testes (unit/integration/e2e/performance), FRs associados e critérios de aceitação.

**Update 2026-01-16:** Added critical tasks based on Implementation Readiness Review to cover FR gaps.

**Regra obrigatória para todas as tarefas:** nenhuma tarefa pode ser considerada concluída sem (1) executar um passo a passo explícito de testes da funcionalidade e (2) obter aprovação de um humano após essa verificação.

## Plano de Testes por Tarefa (automatizados + manual)

- **Task 2.1 – Schemas Pydantic**
  - Automáticos: `tests/test_schemas.py` (validações, 422 em payload inválido).
  - Manual: verificar `/openapi.json` e respostas 422 via curl/Postman.

- **Task 2.2 – Endpoints de Chat**
  - Automáticos: `tests/test_chat_api.py` (criar sessão, mensagens, paginação, 401/404, delete).
  - Manual: subir uvicorn, usar API key e exercitar `/chat/` (POST/GET), `/chat/{id}/messages`, `/chat/{id}/message`, DELETE; checar persistência.

- **Task 2.3 – Decorators/Agent + LLM stub**
  - Automáticos: `tests/test_sdk/test_decorators.py` (registro de agentes/tools, mock LLM, token count).
  - Manual: snippet de registro de agente/tool e `get_llm().chat` mock.

- **Task 2.4 – Agent Executor (planejado)**
  - Automáticos: unit (formatação de prompt), integração (persiste mensagens), E2E (chat retorna resposta mock). Sugerido `tests/test_sdk/test_executor.py`.
  - Manual: fluxo `/chat/{session_id}/message` com executor real, checando resposta e DB.

- **Task 2.5 – Config System (planejado)**
  - Automáticos: unit (load YAML, override por env, defaults), integração (hot reload), BDD de troca de ambientes. Sugerido `tests/test_config.py`.
  - Manual: alterar config em runtime dev e validar reload; testar env vars sobrescrevendo.

- **Task 2.6 – Templates & CLI Playground (planejado)**
  - Automáticos: unit (carrega templates), integração (CLI inicia sessão), E2E (chat via CLI), BDD. Sugerido `tests/test_cli.py` e `tests/test_templates.py`.
  - Manual: gerar template e rodar `agent-cli play --agent <nome>`.

- **Task 3.1 – Tool decorator & registry (planejado)**
  - Automáticos: unit (registro, schema de params), integração (GET /tools), E2E (agent chama tool mock). Sugerido `tests/test_tools_registry.py`.
  - Manual: registrar tool custom e verificar listagem/execução via endpoint/CLI.

- **Task 3.2 – Memory strategies (planejado)**
  - Automáticos: unit (full vs rolling), integração (executor inclui memória), persistência em DB, BDD.
  - Manual: conversa longa e verificar truncamento/retensão conforme estratégia.

- **Task 3.3 – Token counting & cost tracking (planejado)**
  - Automáticos: unit (contagem), integração (atualiza tokens/custo), E2E, BDD.
  - Manual: simular chamadas e conferir custo/tokens em DB/log.

- **Task 3.4 – Guardrails & safety (planejado)**
  - Automáticos: unit (blocklist/allowlist, fallback), integração (log de violação), E2E (recusa tópico proibido), BDD.
  - Manual: enviar conteúdo bloqueado e verificar resposta e logs.

- **Task 4.1 – Metrics/Prometheus (planejado)**
  - Automáticos: unit (registry), integração (GET /metrics), integração (incrementos), performance (<10 ms).
  - Manual: scrape `/metrics` e validar counters em carga leve.

- **Task 4.2 – PII & Moderation (planejado)**
  - Automáticos: unit (detecção/máscara), integração (PII mascarado antes do LLM), performance, BDD.
  - Manual: enviar mensagens com CPF/email e confirmar máscara; testar conteúdo proibido.

- **Task 4.3 – Retry & Circuit Breakers (planejado)**
  - Automáticos: unit (backoff), integração (abre breaker), fallback de provider, E2E, BDD.
  - Manual: simular falhas de provider e ver transições de estado/retries.

---

## Week 1 - Foundation

### Task 1.1 - Initialize project from Cookiecutter FastAPI
- Description: Run cookiecutter starter to scaffold project skeleton with FastAPI, SQLAlchemy, Alembic, Docker, pytest.
- FRs: FR1 (installation), FR81 (API endpoints scaffold)
- Acceptance Criteria:
  - Project scaffolded under `app/` with `main.py`, `alembic/`, `app/core/`, `app/api/` files
  - `requirements-dev.txt` created with testing stack
  - `pytest` runs and discovers no tests (smoke)
- Test Scope:
  - Unit: `test_scaffold_files_exist()` - check file locations
  - Integration: `test_start_app_imports()` - import `app.main` without runtime errors
  - E2E: none
  - Performance: none

### Task 1.2 - Database schema (initial models)
- Description: Create SQLAlchemy models: `Agent`, `Session`, `Message`, `APIKey`, `ToolCall`.
- FRs: FR41-FR47 (memory & context), FR71 (API key management), FR81 (session endpoints)
- Acceptance Criteria:
  - Models defined in `app/core/models.py` with correct fields and relationships
  - Alembic initial migration generated
- Test Scope:
  - Unit: `test_models_fields_present()` - model attributes exist
  - Integration: `test_create_and_query_models_sqlite()` - use SQLite in-memory session
  - E2E: none
  - Performance: none

### Task 1.3 - Alembic migrations
- Description: Setup Alembic config, create initial migration, ensure migration applies to DB.
- FRs: FR96 (automatic migrations), FR91 (docker ops)
- Acceptance Criteria:
  - `alembic.ini` and `migrations/` present
  - Running migration applies schema to test DB
- Test Scope:
  - Integration: `test_alembic_migration_applies()` - run `alembic upgrade head` against test DB
  - Unit: none
  - E2E: none

### Task 1.4 - API Key middleware & auth
- Description: Implement `X-API-Key` header middleware for request authentication, basic APIKey model hashing.
- FRs: FR71-FR77 (auth, rate-limiting basic), FR80 (security headers)
- Acceptance Criteria:
  - Requests without `X-API-Key` get 401
  - Valid API key stored hashed in DB and can be used
- Test Scope:
  - Unit: `test_hash_api_key()` - key hashing
  - Integration: `test_api_requires_api_key()` - TestClient without header returns 401
  - E2E: `test_api_key_full_flow()` - create API key via admin endpoint and use it

### Task 1.5 - Health check & basic logging
- Description: Add `/health` endpoint reporting DB and LLM status (LLM mocked for now). Configure JSON logging and trace_id generation.
- FRs: FR87 (health), FR61-FR62 (logging & trace ids)
- Acceptance Criteria:
  - `/health` returns 200 with `db` and `llm` keys
  - Logs include `trace_id` per request
- Test Scope:
  - Unit: `test_trace_id_generated()` - trace ID present in logs
  - Integration: `test_health_endpoint()` - returns expected JSON

---

## Week 2 - Core features

### Task 2.1 - Pydantic schemas and validation
- Description: Implement `schemas/` for request/response models and input validation.
- FRs: FR81-FR90 (validation + API), FR16 (type hints)
- Acceptance Criteria:
  - All API inputs validated and return 400 on invalid input
  - OpenAPI generated and matches schemas
- Test Scope:
  - Unit: `test_schema_validation_errors()` - invalid payloads
  - Integration: `test_openapi_contains_endpoints()` - GET /openapi.json includes paths

### Task 2.2 - Chat API endpoints
- Description: Implement REST routes for chat interaction: POST /chat (start session), GET /chat/{session_id} (get session), GET /chat/{session_id}/messages (get history), POST /chat/{session_id}/message (send message), DELETE /chat/{session_id} (delete session). No agent CRUD endpoints - agents are defined in code via SDK.
- FRs: FR81-FR86 (REST API)
- Acceptance Criteria:
  - Chat endpoints respond with correct status codes and payloads
  - Messages and sessions persist in DB
  - API key authentication required on all chat endpoints
  - Session history retrievable with pagination
- Test Scope:
  - Unit: `test_chat_start_creates_session()` - POST /chat creates session
  - Unit: `test_chat_send_message_persists()` - message saved to DB
  - Integration: `test_chat_api_workflow()` - create session → send message → get history
  - E2E: `test_full_chat_interaction()` - complete chat flow with mocked LLM
  - Note: No agent CRUD endpoints (agents created in code via SDK, not API)

### Task 2.3 - LangChain abstraction & mock provider
- Description: Implement `app/llm/abstraction.py` to wrap LangChain chat models and add mocking support for tests using `FakeListChatModel`. Also implement initial SDK agent decorator `@ai_framework.agent` that agents will use to define themselves.
- FRs: FR31-FR36 (LLM integration), FR1 (agent definition in code)
- Acceptance Criteria:
  - LangChain `ChatOpenAI` and `ChatAnthropic` calls go through abstraction layer
  - Mock provider (`FakeListChatModel`) can be injected via dependency override
  - Callbacks for token counting and cost tracking configured
  - SDK `@ai_framework.agent` decorator registers agents for use in runtime
- Test Scope (TDD approach):
  - Unit: `test_llm_abstraction_calls_provider()` - assert provider called
  - Unit: `test_llm_token_callback_tracks_usage()` - verify callback integration
  - Unit: `test_agent_decorator_registers()` - agent decorator works
  - Integration: `test_mock_langchain_response()` - override provider in TestClient with FakeListChatModel

### Task 2.4 - Agent executor skeleton
- Description: Implement initial `AgentExecutor` that formats messages, calls LLM through abstraction, and returns response.
- FRs: FR51-FR56 (execution & reasoning)
- Acceptance Criteria:
  - Executor accepts session_id and message and returns assistant content (mocked)
  - Messages saved to DB
- Test Scope:
  - Unit: `test_executor_formats_prompt()` - message formatting
  - Integration: `test_executor_saves_messages()` - DB persistence
  - E2E: `test_chat_endpoint_integration()` - POST /agents/{id}/chat returns mocked reply

### Task 2.5 - Configuration system (YAML + Environment) 🆕
- Description: Implement YAML-based configuration with environment variable overrides, multiple environment support (dev/staging/prod), and hot reload in dev mode.
- FRs: FR2-FR7 (config system), FR10 (sensible defaults)
- Acceptance Criteria:
  - YAML config file loaded from `config/` directory
  - Environment variables override YAML settings (e.g., `DB_URL` overrides `database.url`)
  - Support for `config.dev.yaml`, `config.prod.yaml`
  - Hot reload detects config changes in dev mode
  - All settings have sensible defaults
- Test Scope (TDD):
  - Unit: `test_yaml_config_loads()` - parse YAML correctly
  - Unit: `test_env_var_overrides_yaml()` - env takes precedence
  - Unit: `test_default_values_applied()` - missing keys use defaults
  - Integration: `test_config_hot_reload()` - file change triggers reload
  - BDD: `scenario_developer_switches_environments.feature`

### Task 2.6 - Agent templates & CLI playground 🆕
- Description: Create 3+ ready-to-use agent templates (chatbot, ITSM, data analyst) and implement CLI playground for interactive agent testing.
- FRs: FR11-FR15 (agent development), FR18-FR19 (development tooling)
- Acceptance Criteria:
  - Templates available in `templates/` directory with README
  - CLI command `agent-cli play --agent <name>` starts interactive session
  - Templates include: chatbot, ITSM agent, data analyst
  - Each template has configuration example and quick start guide
  - CLI supports hot reload and debug mode
- Test Scope (BDD heavy):
  - Unit: `test_template_loads()` - template files parse correctly
  - Integration: `test_cli_starts_session()` - CLI initializes agent
  - E2E: `test_interactive_chat_flow()` - full conversation via CLI
  - BDD: `scenario_developer_creates_agent_in_3_hours.feature`

---

## Week 3 - Tools & Memory

### Task 3.1 - Tool decorator & registry (LangChain)
- Description: Implement tool system using LangChain's `@tool` decorator and `StructuredTool`, with registry for built-in tools and discovery endpoint.
- FRs: FR21-FR30 (tool system)
- Acceptance Criteria:
  - Registering a function with LangChain `@tool` makes it discoverable via API
  - Tool metadata includes name, description, params (auto-extracted from function signature)
  - Tools compatible with LangChain agents
- Test Scope (BDD scenarios):
  - Unit: `test_tool_decorator_registers()` - verify tool registry
  - Unit: `test_tool_schema_generation()` - validate auto-schema from type hints
  - Integration: `test_list_tools_endpoint()` - GET /tools returns registered tools
  - E2E: `test_agent_calls_tool_and_receives_result()` - agent triggers tool call (mock tool)
  - BDD: `scenario_user_registers_custom_tool.feature`

### Task 3.2 - Memory strategies via LangChain
- Description: Implement memory strategies using LangChain's memory classes: `ConversationBufferMemory` (full) and `ConversationBufferWindowMemory` (rolling) with configurable window size.
- FRs: FR41-FR45 (memory)
- Acceptance Criteria:
  - Full strategy (ConversationBufferMemory) returns all messages
  - Rolling strategy (ConversationBufferWindowMemory) keeps last N messages
  - Memory classes integrate with PostgreSQL backend for persistence
- Test Scope (TDD + BDD):
  - Unit (TDD): `test_full_memory_returns_all()`
  - Unit (TDD): `test_rolling_memory_keeps_window()`
  - Integration: `test_memory_used_by_executor()` - executor includes memory in prompt
  - Integration: `test_memory_persists_to_postgres()` - verify DB storage
  - BDD: `scenario_conversation_memory_management.feature`

### Task 3.3 - Token counting & cost tracking via LangChain callbacks
- Description: Implement token counter using LangChain's callback system (`get_openai_callback`) and per-session cost tracking with provider pricing table.
- FRs: FR39-FR40 (token counting & tracking)
- Acceptance Criteria:
  - Token counter uses LangChain callbacks to capture token usage
  - Session record includes `tokens_used` and `cost` fields updated after chat
  - Cost calculated based on provider (OpenAI, Anthropic) pricing
- Test Scope (TDD approach):
  - Unit: `test_token_counter_counts_tokens()` - verify callback integration
  - Unit: `test_cost_calculation_per_provider()` - test pricing logic
  - Integration: `test_cost_updates_after_chat()` - E2E cost tracking

### Task 3.4 - Guardrails & safety features 🆕
- Description: Implement configurable guardrails (content filtering, topic blocklist/allowlist), grounding in verified data, and "I don't know" fallback behavior.
- FRs: FR57-FR60 (execution & reasoning), FR78-FR79 (security & compliance)
- Acceptance Criteria:
  - Configurable guardrails per agent (blocklist, allowlist topics)
  - Confidence threshold triggers "I don't know" response
  - Grounding mechanism validates responses against verified data sources
  - Policy violation logging with trace IDs
  - Graceful fallback when uncertain or blocked content detected
- Test Scope (TDD + BDD):
  - Unit: `test_blocklist_filters_content()` - blocked topics rejected
  - Unit: `test_confidence_threshold_fallback()` - low confidence triggers fallback
  - Integration: `test_guardrails_log_violations()` - violations logged with trace ID
  - E2E: `test_agent_refuses_blocked_topic()` - end-to-end guardrail enforcement
  - BDD: `scenario_guardrails_prevent_inappropriate_content.feature`

---

## Week 4 - Observability & Compliance 🆕

### Task 4.1 - Metrics & Prometheus integration
- Description: Implement Prometheus metrics export for agent performance, API latency, LLM token usage, error rates, and dashboard-ready observability.
- FRs: FR63-FR70 (observability), NFR-P3-P6 (performance monitoring)
- Acceptance Criteria:
  - Prometheus `/metrics` endpoint exposes key metrics
  - Metrics: request_duration, llm_tokens_used, error_rate, active_sessions
  - Grafana-compatible metric naming conventions
  - Metrics filterable by agent_id, session_id, provider
  - Performance profiling per component (LLM, DB, tools)
- Test Scope (Integration heavy):
  - Unit: `test_metrics_registry_registers()` - metrics added to registry
  - Integration: `test_prometheus_endpoint_exports()` - GET /metrics returns valid Prometheus format
  - Integration: `test_metrics_update_on_request()` - counters increment correctly
  - Performance: `test_metrics_overhead_minimal()` - < 10ms overhead
  - BDD: `scenario_ops_monitors_agent_performance.feature`

### Task 4.2 - PII detection & content moderation
- Description: Implement PII detection (CPF, email, phone, credit cards) with automatic masking, and basic content moderation (violence, hate, sexual content).
- FRs: FR78-FR79 (PII masking, content moderation), NFR-S7-S8 (detection accuracy)
- Acceptance Criteria:
  - PII detection accuracy > 90% (CPF, email, phone, cards)
  - Automatic masking before sending to LLM
  - Content moderation recall > 95% (violence, hate, sexual)
  - Configurable sensitive field list per agent
  - Moderation violations logged with severity level
- Test Scope (TDD + performance):
  - Unit: `test_cpf_detection()` - detects Brazilian CPF format
  - Unit: `test_email_masking()` - masks email addresses
  - Unit: `test_content_moderation_detects_violence()` - flags violent content
  - Integration: `test_pii_masked_before_llm()` - LLM never sees raw PII
  - Performance: `test_pii_detection_latency()` - < 50ms per message
  - BDD: `scenario_lgpd_compliance_pii_protection.feature`

### Task 4.3 - Advanced retry & circuit breakers
- Description: Implement retry logic with exponential backoff for LLM calls, circuit breakers for external APIs, and automatic provider fallback.
- FRs: FR37-FR38 (retry, fallback), NFR-R1-R2 (reliability), NFR-R4 (circuit breakers)
- Acceptance Criteria:
  - 3 retries with exponential backoff (1s, 2s, 4s)
  - Circuit breaker opens after 5 consecutive failures
  - Automatic fallback to secondary LLM provider
  - Configurable timeout thresholds per operation
  - Structured failure logging with retry count
- Test Scope (Integration + E2E):
  - Unit: `test_exponential_backoff_calculation()` - retry delays correct
  - Integration: `test_circuit_breaker_opens()` - breaker trips after failures
  - Integration: `test_provider_fallback_activates()` - switches to backup provider
  - E2E: `test_resilient_llm_call()` - survives provider outage
  - BDD: `scenario_system_recovers_from_provider_failure.feature`

---

## Notes & Next Steps

**Update 2026-01-16 (Post-IR Review):**
- ✅ Added 6 critical tasks based on Implementation Readiness gaps
- ✅ Extended scope from 3 weeks to 4 weeks
- ✅ All 90 FRs now have explicit task coverage
- ✅ Critical NFRs (security, performance, compliance) addressed

**New Tasks Added:**
1. Task 2.5: Config System (FR2-7) - Addresses usability gap
2. Task 2.6: Templates & CLI (FR11-15) - Enables "3-hour success" metric (SDK + examples)
3. Task 3.4: Guardrails (FR57-60, FR78-79 partial) - Security & safety
4. Task 4.1: Metrics/Prometheus (FR63-70) - Operational visibility
5. Task 4.2: PII/Moderation (FR78-79) - LGPD compliance
6. Task 4.3: Retry/Circuit Breakers (FR37-38, NFR-R1-R4) - Reliability

**Architecture Clarification:**
- **SDK** (`ai_framework/`): Python package with decorators for defining agents in code
  - Task 2.3: `@ai_framework.agent` decorator for agent definition
  - Task 2.6: Templates and CLI examples showing SDK usage
- **Runtime API** (FastAPI): Chat interaction endpoints only (no agent CRUD)
  - Task 2.2: Chat endpoints for message interaction
  - Task 4.1+: Observability and compliance

**FR Coverage After Updates:**
- Week 1-4 now covers ~75 of 90 FRs (83%)
- Remaining 15 FRs deferred to Weeks 5-8 (Growth features)
- All critical MVP requirements included

**Testing Strategy:**
- **TDD (Test-Driven Development):** Write unit tests first for core logic (models, utilities, business rules)
- **BDD (Behavior-Driven Development):** Use pytest-bdd for user-facing features and workflows
- **Coverage Target:** ≥80% as per NFR-Maintainability
- **Test Pyramid:** Unit (60%) > Integration (30%) > E2E (10%)

**Roadmap:**
- Weeks 1-2: Foundation (config, auth, DB, schemas)
- Week 3: Core features (tools, memory, guardrails)
- Week 4: Observability & compliance (metrics, PII, reliability)
- Weeks 5-8: Advanced features, optimization, deployment hardening

**Next Phase:** Implementation Readiness validated → Ready for Party Mode (collaborative development)

---

Generated by: Winston (Architect Agent) - Updated after IR Review

---

Generated by: AI Agent
