---
task_id: 10
name: Sistema de ferramentas (@tool, registry, discovery)
week: 3
status: pendente
related_FRs: [FR21, FR22, FR23, FR24, FR25, FR26, FR27, FR28, FR29, FR30]
related_NFRs: [NFR-Extensibility]
---

## Descrição
Implementar decorator `@tool`, registro de ferramentas, endpoint de discovery e integração inicial com executor.

## Sub-tarefas
- Criar decorator `@tool` em `app/tools/decorator.py`
- Registry de ferramentas (builtin e custom)
- Endpoint GET `/tools` para listar ferramentas
- Integração com AgentExecutor

## Critérios de Aceite
- Função decorada com `@tool` aparece no registry
- Endpoint `/tools` lista todas as ferramentas
- Executor pode chamar ferramenta mock

## FRs/NFRs Relacionados
- FR21-FR30: Tool system
- NFR-Extensibility: Fácil adicionar novas ferramentas

## Escopo de Testes
- **Unitário:**
  - `test_tool_decorator_registers()`
- **Integração:**
  - `test_list_tools_endpoint()`
- **E2E:**
  - `test_agent_calls_tool_and_receives_result()`

## Exemplo de Teste Unitário
```python
def test_tool_decorator_registers():
    ...
```
