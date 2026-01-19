---
task_id: 14
name: Observabilidade (logs, métricas, trace)
week: 4
status: pendente
related_FRs: [FR61, FR62, FR63, FR64, FR65, FR66, FR67, FR68, FR69, FR70]
related_NFRs: [NFR-Observability]
---

## Descrição
Implementar logging estruturado, geração e propagação de trace_id, métricas Prometheus, dashboard básico e filtros de logs.

## Sub-tarefas
- Configurar logging JSON (timestamp, level, trace_id, módulo)
- Gerar trace_id único por request e propagar
- Expor métricas Prometheus (endpoint `/metrics`)
- Implementar filtros de logs por nível e componente
- Dashboard básico (mock)

## Critérios de Aceite
- Logs em JSON, trace_id propagado
- Endpoint `/metrics` retorna métricas
- Filtros de logs funcionam

## FRs/NFRs Relacionados
- FR61-FR70: Observabilidade
- NFR-Observability: Logs e métricas estruturados

## Escopo de Testes
- **Unitário:**
  - `test_log_in_json_format()`
  - `test_trace_id_generated()`
- **Integração:**
  - `test_metrics_endpoint()`
- **E2E:**
  - `test_trace_id_propagation()`

## Exemplo de Teste Unitário
```python
def test_log_in_json_format(caplog):
    ...
```
