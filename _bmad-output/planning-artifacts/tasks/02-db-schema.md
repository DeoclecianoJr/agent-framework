---
task_id: 02
name: Modelagem e migração inicial do banco de dados
week: 1
status: pendente
related_FRs: [FR41, FR42, FR43, FR44, FR45, FR46, FR47, FR71, FR81]
related_NFRs: []
---

## Descrição
Criar modelos SQLAlchemy: Agent, Session, Message, APIKey, ToolCall. Gerar migração inicial com Alembic.

## Sub-tarefas
- Definir modelos em `app/core/models.py`
- Relacionamentos e constraints
- Gerar migration Alembic inicial
- Validar aplicação da migration em banco de teste

## Critérios de Aceite
- Modelos criados com todos os campos e relacionamentos
- Migration inicial criada e aplicável

## FRs/NFRs Relacionados
- FR41-FR47: Memória/contexto
- FR71: API key management
- FR81: Endpoints de sessão

## Escopo de Testes
- **Unitário:**
  - `test_models_fields_present()` — verifica atributos dos modelos
- **Integração:**
  - `test_create_and_query_models_sqlite()` — cria e consulta modelos em SQLite memória
- **E2E:**
  - Não aplicável

## Exemplo de Teste de Integração
```python
def test_create_and_query_models_sqlite(db_session):
    from app.core.models import Agent
    agent = Agent(name='test')
    db_session.add(agent)
    db_session.commit()
    assert db_session.query(Agent).filter_by(name='test').first() is not None
```
