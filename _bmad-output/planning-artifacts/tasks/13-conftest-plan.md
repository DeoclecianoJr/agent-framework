---
task_id: 13
name: Plano de conftest.py e fixtures de teste
week: 1-2
status: pendente
related_FRs: [FR1, FR41, FR71, FR81, FR90]
related_NFRs: [NFR-Maintainability, NFR-Testing]
---

## Descrição
Planejar e implementar `tests/conftest.py` com fixtures compartilhadas para banco, client, API key, LLM mock, dados de teste e factories.

## Sub-tarefas
- Fixture de banco SQLite memória
- Fixture de TestClient FastAPI
- Fixture de API key válida
- Fixture de mock LLM
- Factory Boy para dados (Agent, Session, Message)
- Configuração de markers pytest

## Critérios de Aceite
- Todos os testes podem usar fixtures
- Testes isolados e reprodutíveis

## FRs/NFRs Relacionados
- FR1: Instalação
- FR41: Memória
- FR71: Auth
- FR81: API
- FR90: Validação
- NFR-Maintainability: Testes fáceis de manter

## Escopo de Testes
- **Unitário/Integração:**
  - Todos os testes usam fixtures
  - Testes de isolamento e reprodutibilidade

## Exemplo de Uso
```python
def test_agent_factory(agent_factory):
    agent = agent_factory()
    assert agent.name.startswith('test-agent')
```
