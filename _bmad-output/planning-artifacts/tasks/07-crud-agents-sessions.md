---
task_id: 07
name: Endpoints CRUD para Agents e Sessions
week: 2
status: pendente
related_FRs: [FR81, FR82, FR83, FR84, FR85, FR86]
related_NFRs: [NFR-Performance]
---

## Descrição
Implementar rotas REST para agents (POST/GET/PUT/DELETE) e sessions (POST/GET/DELETE), persistindo no banco.

## Sub-tarefas
- Criar rotas em `app/api/routes/agents.py` e `sessions.py`
- Implementar métodos CRUD completos
- Garantir persistência e resposta correta
- Testar status codes e payloads

## Critérios de Aceite
- Endpoints CRUD funcionam e persistem dados
- Status codes e payloads corretos

## FRs/NFRs Relacionados
- FR81-FR86: REST API
- NFR-Performance: Respostas rápidas

## Escopo de Testes
- **Unitário:**
  - `test_agent_create_valid_payload_returns_201()`
- **Integração:**
  - `test_agent_crud_workflow()` — create, retrieve, update, delete
- **E2E:**
  - `test_full_agent_session_flow()` — criar agent, criar session, chat (LLM mock)

## Exemplo de Teste de Integração
```python
def test_agent_crud_workflow(client):
    # Cria, recupera, atualiza e deleta um agent
    ...
```
