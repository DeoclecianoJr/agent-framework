---
task_id: 05
name: Health check endpoint e logging estruturado
week: 1
status: pendente
related_FRs: [FR87, FR61, FR62]
related_NFRs: [NFR-Observability]
---

## Descrição
Adicionar endpoint `/health` que reporta status do banco e do LLM (mock). Configurar logging JSON estruturado e geração de trace_id por request.

## Sub-tarefas
- Criar rota `/health` (GET)
- Checar conexão com banco e provider LLM (mock)
- Configurar logging JSON (timestamp, level, trace_id)
- Gerar trace_id único por request

## Critérios de Aceite
- `/health` retorna 200 com chaves `db` e `llm`
- Logs em JSON, cada request com trace_id

## FRs/NFRs Relacionados
- FR87: Health check
- FR61: Structured logging
- FR62: Trace IDs
- NFR-Observability: Logs estruturados

## Escopo de Testes

### O que deve ser testado
- Endpoint `/health` responde 200 e retorna status do banco e LLM
- Logs em formato JSON, com trace_id único por request
- Trace_id propagado em toda a requisição

### Tipos de Teste
- **Unitário:**
  - Verificar geração de trace_id
  - Validar formato do log JSON
- **Integração:**
  - Chamar `/health` e validar resposta
  - Verificar trace_id no log após request
- **E2E:**
  - Simular request completa e garantir trace_id do início ao fim

### Casos de Sucesso
- `/health` retorna 200 e JSON esperado
- Todos os logs possuem trace_id
- Trace_id igual do início ao fim da request

### Casos de Falha
- `/health` retorna erro
- Log sem trace_id
- Trace_id muda durante a request

### Cobertura Esperada
- 100% dos fluxos de health/log/trace testados

### Exemplos de Testes
```python
def test_trace_id_generated(caplog):
    # Simula request e verifica trace_id no log
    ...

def test_health_endpoint(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.json()
    assert 'db' in data and 'llm' in data
```
