---
task_id: 06
name: Schemas Pydantic e validação de entrada
week: 2
status: pendente
related_FRs: [FR81, FR82, FR83, FR84, FR85, FR86, FR90, FR16]
related_NFRs: [NFR-Maintainability]
---

## Descrição
Implementar schemas Pydantic para requests/responses e validação automática de entrada nas rotas.

## Sub-tarefas
- Criar `app/core/schemas.py` com modelos Pydantic
- Validar todos os campos obrigatórios
- Configurar tratamento de erro 400 para payload inválido
- Garantir geração automática do OpenAPI

## Critérios de Aceite
- Payloads inválidos retornam 400
- OpenAPI reflete todos os schemas

## FRs/NFRs Relacionados
- FR81-FR86: Endpoints REST
- FR90: Validação
- FR16: Type hints
- NFR-Maintainability: Facilitar manutenção

## Escopo de Testes
- **Unitário:**
  - `test_schema_validation_errors()` — payloads inválidos
- **Integração:**
  - `test_openapi_contains_endpoints()` — OpenAPI inclui todos os endpoints

## Exemplo de Teste Unitário
```python
def test_schema_validation_errors(client):
    response = client.post('/agents', json={})
    assert response.status_code == 400
```
