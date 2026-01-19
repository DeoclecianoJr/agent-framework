---
task_id: 09
name: Abstração LLM e mock provider
week: 2
status: pendente
related_FRs: [FR31, FR32, FR33, FR34, FR35, FR36, FR37, FR38, FR39, FR40]
related_NFRs: [NFR-Performance]
---

## Descrição
Implementar camada de abstração para LLMs (OpenAI, Anthropic, Azure) e provider mock para testes.

## Sub-tarefas
- Criar `app/llm/abstraction.py`
- Interface unificada para múltiplos providers
- Suporte a mock provider para testes
- Injeção de dependência para override em testes

## Critérios de Aceite
- Chamada ao LLM sempre via abstração
- Mock provider pode ser usado em testes

## FRs/NFRs Relacionados
- FR31-FR40: Integração LLM, mocking, token/cost

## Escopo de Testes
- **Unitário:**
  - `test_llm_abstraction_calls_provider()`
- **Integração:**
  - `test_mock_litellm_response()`

## Exemplo de Teste Unitário
```python
def test_llm_abstraction_calls_provider(mocker):
    mock = mocker.patch('litellm.completion')
    ...
```
