---
task_id: 11
name: Estratégias de memória (Full/Rolling)
week: 3
status: pendente
related_FRs: [FR41, FR42, FR43, FR44, FR45, FR46, FR47, FR48, FR49, FR50]
related_NFRs: [NFR-Performance]
---

## Descrição
Implementar estratégias de memória: FullMemoryStrategy (tudo) e RollingMemoryStrategy (últimas N mensagens), configuráveis.

## Sub-tarefas
- Criar classes em `app/agents/memory.py`
- Configuração de tamanho da janela (rolling)
- Integração com executor
- Testes de persistência e recuperação

## Critérios de Aceite
- Full retorna todas as mensagens
- Rolling retorna apenas últimas N
- Executor usa estratégia correta

## FRs/NFRs Relacionados
- FR41-FR50: Memória/contexto

## Escopo de Testes
- **Unitário:**
  - `test_full_memory_returns_all()`
  - `test_rolling_memory_keeps_window()`
- **Integração:**
  - `test_memory_used_by_executor()`

## Exemplo de Teste Unitário
```python
def test_rolling_memory_keeps_window():
    ...
```
