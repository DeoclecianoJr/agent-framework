---
task_id: 12
name: Token counting e cost tracking
week: 3
status: pendente
related_FRs: [FR39, FR40]
related_NFRs: [NFR-Performance, NFR-Observability]
---

## Descrição
Implementar utilitário para contagem de tokens e cálculo de custo por sessão, com tabela de preços mock.

## Sub-tarefas
- Criar utilitário em `app/llm/token_counter.py`
- Mock de tabela de preços por provider/model
- Atualizar campos `tokens_used` e `cost` na sessão
- Integração com executor

## Critérios de Aceite
- Token counter retorna inteiro correto
- Cost tracking atualiza sessão

## FRs/NFRs Relacionados
- FR39-FR40: Token counting/tracking

## Escopo de Testes
- **Unitário:**
  - `test_token_counter_counts_tokens()`
- **Integração:**
  - `test_cost_updates_after_chat()`

## Exemplo de Teste Unitário
```python
def test_token_counter_counts_tokens():
    ...
```
