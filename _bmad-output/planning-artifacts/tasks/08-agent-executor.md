---
task_id: 08
name: Implementação do AgentExecutor
week: 2
status: pendente
related_FRs: [FR51, FR52, FR53, FR54, FR55, FR56, FR57, FR58, FR59, FR60]
related_NFRs: [NFR-Performance, NFR-Maintainability]
---

## Descrição
Implementar o núcleo do AgentExecutor: recebe mensagem, consulta memória, chama LLM via abstração, executa ferramentas, retorna resposta e salva histórico.

## Sub-tarefas
- Criar classe `AgentExecutor` em `app/agents/executor.py`
- Integrar com memória (Full/Rolling)
- Chamar LLM via abstração
- Suportar execução de ferramentas (mock inicialmente)
- Persistir mensagens e tool calls
- Tratar erros e fallback

## Critérios de Aceite
- Executor processa mensagem e retorna resposta (mock)
- Mensagens e tool calls persistidas
- Suporta fallback e erros

## FRs/NFRs Relacionados
- FR51-FR60: Execução, reasoning, fallback
- NFR-Performance: Resposta < 3s (mock)

## Escopo de Testes
- **Unitário:**
  - `test_executor_formats_prompt()`
  - `test_executor_handles_tool_call()`
- **Integração:**
  - `test_executor_saves_messages()`
  - `test_executor_with_memory()`
- **E2E:**
  - `test_chat_endpoint_integration()`

## Exemplo de Teste Unitário
```python
def test_executor_formats_prompt():
    executor = AgentExecutor()
    prompt = executor.format_prompt('user', 'Olá')
    assert 'Olá' in prompt
```
